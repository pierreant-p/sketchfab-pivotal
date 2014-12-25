import argparse
import json
import re
import requests

from settings import (
    API_TOKEN,
    USER_ID,
    PROJECT_ID
)

# Possible command-line actions
EPIC_NEXT_HOTFIX = 'epic_next_hotfix'
EPIC_NEXT_RELEASE = 'epic_next_release'

# Handle arguments
parser = argparse.ArgumentParser(description='Automate some pivotal tasks.')
parser.add_argument('action', choices=[
    EPIC_NEXT_RELEASE,
    EPIC_NEXT_HOTFIX
])


base_url = "https://www.pivotaltracker.com/services/v5"
project_url = "{}/projects/{}".format(base_url, PROJECT_ID)
labels_url = "{}/labels".format(project_url)
epics_url = "{}/epics".format(project_url)
stories_url = "{}/stories".format(project_url)

VERSION_RE = re.compile('(\d+)\.(\d+).(\d+)')

PIVOTAL_HEADERS = {
    'X-TrackerToken': API_TOKEN,
    'content-type': 'application/json'
}


def fetch_release_epics():
    url = "{}?filter=name:release".format(epics_url)
    response = requests.get(url, headers=PIVOTAL_HEADERS)

    return response


def create_version_epic(version):
    # first, check if there is already an epic for this version
    check_url = "{}?filter=name:?{}".format(epics_url, version)
    response = requests.get(check_url, headers=PIVOTAL_HEADERS).json()

    if len(response) > 0:
        print "There is already an epic for this version: {}".format(response[0]['url'])
        return

    print "Creating epic for version {}".format(version)

    name = "Release v{}".format(version)
    data = {
        'name': name,
        'label': {
            'name': "v{}".format(version)
        }
    }
    response = requests.post(epics_url, data=json.dumps(data), headers=PIVOTAL_HEADERS).json()

    # create the release story
    create_release_story(version)

    print "Epic created: {}".format(response['url'])


def fetch_version_label(version):
    response = requests.get(labels_url, headers=PIVOTAL_HEADERS)
    labels = response.json()

    search = 'v{}'.format(version)

    for label in labels:
        if label['name'] == search:
            return label['id']

    return None


def oldest_of(version_1, version_2):
    """Return True if :version_1 is older than :version_2"""
    major_1, minor_1, hotfix_1 = [int(v) for v in version_1.split('.')]
    major_2, minor_2, hotfix_2 = [int(v) for v in version_2.split('.')]

    if major_1 != major_2:
        return version_1 if major_1 > major_2 else version_2

    elif minor_1 != minor_2:
        return version_1 if minor_1 > minor_2 else version_2

    elif hotfix_1 != hotfix_2:
        return version_1 if hotfix_1 > hotfix_2 else version_2

    else:
        # both versions are equal
        return version_1


def bump_release(version):
    major, minor, hotfix = [int(v) for v in version.split('.')]

    minor += 1
    hotfix = 0

    return "{}.{}.{}".format(major, minor, hotfix)


def bump_hotfix(version):
    major, minor, hotfix = [int(v) for v in version.split('.')]

    hotfix += 1

    return "{}.{}.{}".format(major, minor, hotfix)


def get_latest_version():
    latest_version = '0.0.0'
    epics = fetch_release_epics().json()

    for epic in epics:
        match = VERSION_RE.search(epic['name'])
        if match:
            version = match.group(0)
            latest_version = oldest_of(version, latest_version)

    return latest_version


def create_next_hotfix_epic():
    """Create an epic for the next hotfix"""
    latest_version = get_latest_version()
    hotfix_version = bump_hotfix(latest_version)
    create_version_epic(hotfix_version)


def create_next_release_epic():
    """Create an epic for the next release"""
    latest_version = get_latest_version()
    release_version = bump_release(latest_version)
    create_version_epic(release_version)


def create_release_story(version):
    """Create a release story for the epic """
    data = {
        'name': 'release {}'.format(version),
        'story_type': 'release',
        'labels': [{
            'name': 'v{}'.format(version)
        }],
        'owner_ids': [USER_ID],
        'requested_by_id': USER_ID
    }

    response = requests.post(stories_url, data=json.dumps(data), headers=PIVOTAL_HEADERS)

    return response


if __name__ == "__main__":
    args = parser.parse_args()

    if args.action == EPIC_NEXT_RELEASE:
        create_next_release_epic()

    elif args.action == EPIC_NEXT_HOTFIX:
        create_next_hotfix_epic()
