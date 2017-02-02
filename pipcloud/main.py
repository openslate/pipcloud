from __future__ import print_function

import argparse
import sys
import os
import glob
import boto3
import json

from subprocess import call, CalledProcessError
from botocore.errorfactory import ClientError
from jinja2 import Environment, PackageLoader


class S3(object):
    connection = None

    @staticmethod
    def get_instance(args):
        if not S3.connection:
            S3.connection = S3(args)
        return S3.connection

    def __init__(self, args):
        self.s3 = boto3.resource('s3', region_name=args.region)
        self.bucket = args.BUCKET
        self.verbose = args.verbose

    def get(self, path, download=True):
        try:
            if self.verbose:
                print("Getting file s3://%s%s" % (self.bucket, path))
            if path.startswith('/'):
                path = path[1:]
            f = self.s3.Object(self.bucket, path).get()
            if download:
                return f['Body'].read()
            else:
                return f
        except ClientError:
            return None

    def put(self, path, data, headers):
        if headers.get('ContentType', None) is None:
            raise RuntimeError("At least the Content-Type header is required")
        self.s3.Bucket(self.bucket).put_object(
            Key=path.lstrip("/"),
            Body=data,
            ACL='public-read',
            **headers
        )


def generate_index(typ, data, name=None):
    if typ == 'package':
        return Environment(
            loader=PackageLoader('pipcloud', 'templates')
        ).get_template('package_index.html.j2').render({
            'name': name,
            'files': data,
        })
    elif typ == 'repo':
        return Environment(
            loader=PackageLoader('pipcloud', 'templates')
        ).get_template('repo_index.html.j2').render({'packages': data})


def update_index(args, name, files):
    s3 = S3.get_instance(args)

    new_index = None
    index = s3.get('/.pipcloud.json')
    print("Got json data of len %d" % len(index))
    if index:
        new_index = json.loads(index)
    else:
        new_index = {}
    if new_index.get(name, None) is None:
        new_index[name] = []
    new_index[name].extend(files)

    new_index[name] = list(set(new_index[name]))

    repo_index = generate_index('repo', new_index)
    package_index = generate_index('package', new_index, name)

    s3.put('/.pipcloud.json', json.dumps(new_index), {
        'ContentType': 'application/json',
        'CacheControl': 'public, must-revalidate, proxy-revalidate, max-age=0',
    })

    s3.put('/index.html', repo_index, {
        'ContentType': 'text/html',
        'CacheControl': 'public, must-revalidate, proxy-revalidate, max-age=0',
    })

    s3.put('/%s/index.html' % name, package_index, {
        'ContentType': 'text/html',
        'CacheControl': 'public, must-revalidate, proxy-revalidate, max-age=0',
    })


class FileAlreadyExistsException(Exception):
    pass


def check_exists(args, name, files):
    s3 = S3.get_instance(args)
    for f in files:
        if s3.get('/%s/%s' % (name, stripdist(f)), download=False) is not None:
            raise FileAlreadyExistsException("Pass -f to force overwrite")
        else:
            if args.verbose:
                print("File /%s/%s not found" % (name, stripdist(f)))


def stripdist(f):
    return f[f.rfind("/")+1:]


def upload(args, name, files):
    s3 = S3.get_instance(args)

    if not args.force:
        check_exists(args, name, files)

    for f in files:
        print("Uploading %s -> '/%s/%s'" % (f, name, stripdist(f)))
        s3.put('/%s/%s' % (name, stripdist(f)), open(f, 'rb'), {
            'ContentType': 'application/x-gzip',
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--region', help='S3 region')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Overwrite existing packages', default=False)

    parser.add_argument('-n', '--no-wheel', action='store_true',
                        help="Don't build wheel", default=False)

    parser.add_argument('-s', '--wheel-only', action='store_true',
                        help="Only build wheel", default=False)

    parser.add_argument('-v', '--verbose', action='store_true', default=False)

    parser.add_argument('-p', '--setup_path', default='setup.py',
                        help='path to setup.py')

    parser.add_argument('NAME', help='package name')
    parser.add_argument('BUCKET', help='s3 bucket name/')

    args = parser.parse_args(sys.argv[1:])

    cmd = ['python', args.setup_path]

    if not args.wheel_only:
        cmd.extend(['sdist', '--formats', 'gztar'])
    if not args.no_wheel or args.wheel_only:
        cmd.append('bdist_wheel')
    try:
        print("Running %s" % ' '.join(cmd))
        with open(os.devnull, 'wb') as ofp:
            call(cmd, stdout=ofp, stderr=ofp)
    except CalledProcessError as e:
        raise RuntimeError(e.output.rstrip())

    name = args.NAME
    files = glob.glob('./dist/*')
    upload(args, name, files)
    update_index(args, name, files)
