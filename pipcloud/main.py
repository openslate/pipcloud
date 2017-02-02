from __future__ import print_function

import argparse
import sys
import re
import glob
import boto3
import json

from subprocess import check_output, CalledProcessError
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
        self.bucket = args.S3URI[5:]

    def get(self, path):
        try:
            return self.s3.Object(self.bucket, path).get()['Body'].read()
        except ClientError:
            return None

    def put(self, path, data, headers):
        if headers.get('ContentType', None) is None:
            raise RuntimeError("At least the Content-Type header is required")
        self.s3.Object(self.bucket, path.lstrip("/")).put(
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
            'files': data[name],
        })
    elif typ == 'repo':
        return Environment(
            loader=PackageLoader('pipcloud', 'templates')
        ).get_template('repo_index.html.j2').render({'packages': data})


def update_index(args, name, files):
    s3 = S3.get_instance(args)

    new_index = None
    index = s3.get('/.pipcloud.json')
    if index:
        new_index = json.loads(index)
    else:
        new_index = {}
    if new_index.get(name, None) is None:
        new_index[name] = []
    new_index[name].extend(files)

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


def upload(args, name, files):
    s3 = S3.get_instance(args)
    for f in files:
        with open(f, 'rb') as fp:
            s3.put('/%s/%s' % (name, f), fp.read(), {
                'ContentType': 'application/x-gzip',
            })


def find_package_name(text):
    match = re.search('^(copying files to|making hard links in) (.+)\.\.\.',
                      text, flags=re.MULTILINE)

    if not match:
        raise RuntimeError('Package name not found in:\n' + text)

    return match.group(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--region', help='S3 region')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Overwrite existing packages')
    parser.add_argument('-n', '--no-wheel', action='store_false',
                        help="Don't build wheel")
    parser.add_argument('-s', '--wheel-only', action='store_true',
                        help="Only build wheel")
    parser.add_argument('S3URI', help='s3://mybucket/path/')

    args = parser.parse_args(sys.argv[1:])

    cmd = ['python', 'setup.py']
    if not args.wheel_only:
        cmd.extend(['sdist', '--formats', 'gztar'])
    if not args.no_wheel or args.wheel_only:
        cmd.append('bdist_wheel')
    try:
        output = check_output(cmd)
    except CalledProcessError as e:
        raise RuntimeError(e.output.rstrip())

    name = find_package_name(output)
    files = glob.glob('./dist/*')
    upload(args, name, files)
    update_index(args, name, files)
