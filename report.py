import argparse
import datetime
import json
import os.path

import dogpile.cache
import requests


DEBUG = False

DATETIME_FORMAT = '%Y-%m-%d %I%p UTC'

# stackalytics.com is way faster than stackalytics.o.o
API_ENDPOINT = 'http://stackalytics.com/api/1.0'

GERRIT_EVENT_TYPES = (
    'Code-Review', 'Workflow', 'Self-Code-Review', 'Self-Workflow')


CACHE_DIR = '/tmp/stackalytics-report'
if not os.path.exists(CACHE_DIR):
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


def debug(d):
    print(json.dumps(d, indent=4, sort_keys=True))


def summarize(events, gerrit_user_ids, project):
    for event in events:
        if not gerrit_user_ids or event['gerrit_id'] in gerrit_user_ids:
            if not project or event['module'] == project:
                # When?
                message = ['[{date_str}]']

                # Who?
                message.append('{gerrit_id} ({company_name})')

                # What?
                if event['type'] in ('Workflow', 'Self-Workflow'):
                    if event['value'] == -1:
                        message.append('WIP\'d')
                    elif event['value'] == 1:
                        message.append('approved')
                    else:
                        debug(event)
                        quit()
                elif event['type'] in ('Code-Review', 'Self-Code-Review'):
                    if event['value'] == 2:
                        message.append('+2\'d')
                    elif event['value'] == 1:
                        message.append('+1\'d')
                    elif event['value'] == -1:
                        message.append('-1\'d')
                    elif event['value'] == -2:
                        message.append('blocked')
                    else:
                        debug(event)
                        quit()
                elif event['type'] in ('Abandon', 'Self-Abandon'):
                    message.append('abandoned')
                else:
                    debug(event)
                    quit()

                message.append('"{parent_subject}" ({parent_number})')

                # Where?
                message.append('in {module}.')

                message = u' '.join(message)
                print(message.format(**event))


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
    start_date, end_date = compute_date_range(args.reporting_period)

    print(
        '{days:d} Day Report ({start} to {end})\n'.format(**{
            'days': args.reporting_period,
            'start': format_timestamp(start_date),
            'end': format_timestamp(end_date),
        })
    )

    summarize(
        activity(start_date, end_date),
        args.gerrit_user_ids,
        args.project)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate a report from Stackalytics on contributor '
                    'activity.')
    parser.add_argument(
        '--debug', action='store_true', default=False,
        help='Enable debugging output.')
    parser.add_argument(
        '--reporting-period', type=int, default=7,
        help='Period (in days) to report on.')
    parser.add_argument(
        '--project',
        help='Project to report on.')
    parser.add_argument(
        'gerrit_user_ids', nargs=argparse.REMAINDER,
        help='Specify gerrit users to filter on.')
    args = parser.parse_args()
    DEBUG = args.debug
    main(args)
