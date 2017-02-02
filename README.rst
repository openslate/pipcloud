pipcloud
========

pipcloud is a CLI tool for creating a Python Package Repository in an S3 bucket.

Installation
------------

Install the latest version::

    pip install pipcloud

Usage
-----

You can now use ``pipcloud`` to create Python packages and upload them to your S3 bucket.::

    pipcloud [-p /path/to/setup.py] projectname s3://my-bucket


Installing packages
-------------------

Install your packages using ``pip`` by pointing the ``--extra-index-url`` to your CloudFront distribution (optionally followed by a secret subdirectory):::

    pip install --upgrade awesome-project --extra-index-url https://pypi.example.com/SECRET/

Alternatively, you can configure the index URL in ~/.pip/pip.conf or
/etc/pip.conf:::

    [global]
    extra-index-url = https://pypi.example.com/SECRET/
