pipcloud
========

pipcloud is a CLI tool for creating a Python Package Repository in an S3 bucket.

Installation
------------

Install the latest version::

    pip install pipcloud

Usage
-----

The s3 bucket you choose should be configured to allow "website hosting" and the
index document should be set to "index.html".

You can now use ``pipcloud`` to create Python packages and upload them to your S3 bucket.::

    pipcloud [-p /path/to/setup.py] projectname my-bucket


Installing packages
-------------------

Install your packages using ``pip`` by pointing the ``--extra-index-url`` to your s3 url::

    pip install --upgrade prjectname --extra-index-url
    http://my-bucket.s3-website-us-east-1.amazonaws.com

Alternatively, you can configure the index URL in ~/.pip/pip.conf or
/etc/pip.conf:::

    [global]
    extra-index-url = http://my-bucket.s3-website-us-east-1.amazonaws.com/
    trusted-hosts = my-bucket.s3-website-us-east-1.amazonaws.com
