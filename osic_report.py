import argparse
import datetime
import os.path

import dogpile.cache
import requests


DEBUG = False

DATETIME_FORMAT = '%Y-%m-%d %I%p UTC'

# stackalytics.com is way faster than stackalytics.o.o
API_ENDPOINT = 'http://stackalytics.com/api/1.0'

ACTIVITY_ATTRIBUTES = (
    'blueprint_id_count',
    'branch',
    'bug_id_count',
    'company_name',
    'module',
    'gerrit_id',
    'parent_blueprint_id_count',
    'parent_gerrit_id',
    'parent_branch',
    'parent_bug_id_count',
    'parent_company_name',
    'parent_module',
    'parent_number',
    'parent_open',
    'parent_project',
    'parent_record_type',
    'parent_release',
    'parent_status',
    'patch',
    'patch_blueprint_id_count',
    'patch_branch',
    'patch_bug_id_count',
    'patch_company_name',
    'patch_gerrit_id',
    'patch_number',
    'patch_record_type',
    'patch_week',
    'record_type',
    'release',
    'type',
)

GERRIT_EVENT_TYPES = (
    'Code-Review', 'Workflow', 'Self-Code-Review', 'Self-Workflow')


CACHE_DIR = '/tmp/stackalytics-collaboration-report'
if not os.path.exists(CACHE_DIR):
    print('Creating %s' % CACHE_DIR)
    os.makedirs(CACHE_DIR, 0o0700)

CACHE = dogpile.cache.make_region().configure(
    'dogpile.cache.dbm',
    expiration_time=3600,
    arguments={
        'filename': '%s/cache.dbm' % CACHE_DIR,
    }
)


def format_timestamp(timestamp):
    s = datetime.datetime.fromtimestamp(timestamp).strftime(DATETIME_FORMAT)

    # Post-process to replace '...-2016 02PM' with '...-2016 2PM'
    return s.replace(' 0', ' ')


def compute_date_range(days_ago):
    utc_today = datetime.datetime.utcnow()

    # Run reports from the top of the hour.
    utc_today = utc_today.replace(minute=0, second=0, microsecond=0)

    delta = datetime.timedelta(days=days_ago)
    epoch_dt = datetime.datetime(1970, 1, 1)

    end_epoch = int((utc_today - epoch_dt).total_seconds())
    start_epoch = int((utc_today - delta - epoch_dt).total_seconds())
    return start_epoch, end_epoch


@CACHE.cache_on_arguments()
def GET(url, params):
    resp = requests.get(url, params=params)
    if DEBUG:
        print('GET %s' % resp.url)
    resp.raise_for_status()
    data = resp.json()
    return data


def report_interactions(events, companies):
    code_review_interactions = set()
    contributors = set()
    project_interactions = set()
    interaction_types = set()
    for event in events:
        if set(companies).issubset(set(event['companies_involved'])):
            project_interactions.add(event['parent_project'])
            if event['type'] in GERRIT_EVENT_TYPES:
                # Parent number is the code review number.
                code_review_interactions.add(int(event['parent_number']))
            else:
                interaction_types.add(event['type'])

            for prefix in ('', 'parent_', 'patch_'):
                if event['%scompany_name' % prefix] in companies:
                    contributors.add(event['%sgerrit_id' % prefix])

    print(
        '%d contributors collaborated in %d code reviews in the following '
        'projects:\n' % (
            len(contributors),
            len(code_review_interactions)))

    for project in project_interactions:
        print('- %s' % project)

    if interaction_types:
        print('NOTE: Other types of interaction: %r' % interaction_types)


def activity(start_date, end_date):
    per_page = 1000
    page = 0

    while True:
        params = dict(
            page_size=per_page,
            start_record=page * per_page,
            start_date=start_date,
            end_date=end_date)

        data = GET(API_ENDPOINT + '/activity', params)
        events = data['activity']

        for event in events:
            yield event

        if not events or len(events) < per_page:
            # Incomplete result set, we're done!
            return

        page += 1


def main(args):
    filtered_events = []
    start_date, end_date = compute_date_range(args.reporting_period)
    for event in activity(start_date, end_date):
        # Filter out the attributes we don't care about.
        for key in event.keys():
            if key not in ACTIVITY_ATTRIBUTES:
                del event[key]

        # Filter out patches that do not involve our target organizations.
        event['companies_involved'] = list(set([
            event['company_name'],
            event['patch_company_name'],
            event['parent_company_name']]))
        if not set(event['companies_involved']).intersection(args.companies):
            continue

        # print(json.dumps(event, indent=4, sort_keys=True))
        filtered_events.append(event)

    print(
        '%(days)d Day Report (%(start)s to %(end)s)\n' % {
            'days': args.reporting_period,
            'start': format_timestamp(start_date),
            'end': format_timestamp(end_date),
        })

    report_interactions(filtered_events, args.companies)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate a report from Stackalytics on the collaboration '
                    'between two organizations')
    parser.add_argument(
        '--debug', action='store_true', default=False,
        help='Enable debugging output.')
    parser.add_argument(
        '--reporting-period', type=int, default=7,
        help='Period (in days) to report on.')
    parser.add_argument(
        'companies', nargs=argparse.REMAINDER,
        help='Specify companies to filter on.')
    args = parser.parse_args()
    DEBUG = args.debug
    main(args)
