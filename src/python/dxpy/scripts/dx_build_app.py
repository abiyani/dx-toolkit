#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.ERROR)

import os, sys, json, fileinput, re, subprocess, argparse
from datetime import datetime
import dxpy, dxpy.app_builder

parser = argparse.ArgumentParser(prog="dx-build-app", description="Upload a DNAnexus applet")
parser.add_argument("src_dir", help="App or applet source directory")
parser.add_argument("-f", "--overwrite", help="Remove existing applets of the same name", action='store_true', default=False)
parser.add_argument("-a", "--create-app", help="Create an app from the applet", action='store_true', default=False)
parser.add_argument("-p", "--destination-project", help="Insert the applet into the project with the specified project ID", default=None)
parser.add_argument("--publish", help="Publish the app after it has been created.", action='store_true', default=False)
parser.add_argument("-b", "--bill-to", help="Owner (username or organization) to bill for the app", default=None)
parser.add_argument("--no-dx-toolkit-autodep", help="Do not auto-insert the dx-toolkit dependency if it's absent from the runSpec", action='store_true', default=False)

def get_timestamp_version_suffix():
    return "+build." + datetime.today().strftime('%Y%m%d.%H%M')

def get_version_suffix(src_dir):
    # If anything goes wrong, fall back to the date-based suffix.
    try:
        if os.path.exists(os.path.join(src_dir, ".git")):
            abbrev_sha1 = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=src_dir).strip()[:7]
            return "+git." + abbrev_sha1
    except:
        pass
    return get_timestamp_version_suffix()


def main():
    args = parser.parse_args()

    if not os.path.isdir(args.src_dir):
        parser.error("%s is not a directory" % args.src_dir)

    if not os.path.exists(os.path.join(args.src_dir, "dxapp.json")):
        parser.error("Directory %s does not contain dxapp.json: not a valid DNAnexus applet source directory" % args.src_dir)

    if args.create_app and not os.path.exists(os.path.join(args.src_dir, "dxapp.json")):
        parser.error("Directory %s does not contain dxapp.json: not a valid DNAnexus app source directory" % args.src_dir)

    dxpy.app_builder.build(args.src_dir)
    bundled_resources = dxpy.app_builder.upload_resources(args.src_dir,
                                                          project=args.destination_project)

    applet_id = dxpy.app_builder.upload_applet(args.src_dir, bundled_resources,
                                               overwrite=args.overwrite,
                                               project=args.destination_project,
                                               dx_toolkit_autodep = (not args.no_dx_toolkit_autodep))

    print >> sys.stderr, "Created applet " + applet_id + " successfully"

    if args.create_app:
        with open(os.path.join(args.src_dir, "dxapp.json")) as app_desc:
            app_json = json.load(app_desc)
        version = app_json['version']
        try_versions = [version, version + get_version_suffix(args.src_dir)]

        app_id = dxpy.app_builder.create_app(applet_id, args.src_dir,
                                             publish=args.publish,
                                             set_default=args.publish,
                                             billTo=args.bill_to,
                                             try_versions=try_versions)
        print >> sys.stderr, "Created app " + app_id + " successfully"
        print json.dumps(dxpy.api.appDescribe(app_id))
    else:
        print json.dumps(dxpy.api.appletDescribe(applet_id))

    #print json.dumps(dxpy.api.appletGet(applet_id))

if __name__ == '__main__':
    main()
