import argparse
import datetime

import requests


LAUNCHPAD_IDS = [
    'xuhj', 'ankur-gupta-f', 'annegentle', 'alexandra-settle',
    'byron-mccollum', 'bmoss', 'brian-rosmaita', 'kevin-carter', 'daz',
    'wei-d-chen', 'dolph', 'dstanek', 'egle', 'ganesh-mahalingam', 'gus',
    'hemanth-makkapati', 'joshua.hesketh', 'johngarbutt', 'jim-rollenhagen',
    'kennycjohnston', 'ldbragst', 'lianhau-lu', 'loquacity', 'madorn',
    'malini-k-bhandaru', 'manjeet-s-bhatia', 'matt-O', 'rackerhacker',
    'mikalstill', 'john-d-perkins', 'mrda', 'npustchi', 'neillc', 'rnortman',
    'ntpttr', 'jesse-pretorius', 'paul-dardeau', 'paul-e-luse', 'r1chardj0n3s',
    'ronald-de-rose', 'ionosphere80', 'sfinucane', 'shashirekha-j-gundur',
    'sumant-murke', 'amy-marrich', 'steve-lewis', 'o-tony', 'xek',
    'yalei-wang', 'yamahata', 'saisrikiran-mudigonda', 'electrocucaracha',
    'castulo-martinez', 'joshua-l-white'
]


def main():
    parser = argparse.ArgumentParser(
        description='Generate a report from Stackalytics on the collaboration '
                    'between two organizations')
    parser.add_argument(
        '--reporting-period', type=int, default=7,
        help='Period (in days) to report on.')
    args = parser.parse_args()

    # FIXME(lbragstad): For some reason the following request doesn't work
    # against stackalytics with python requests. It does work if you copy that
    # same url and use it with cURL. I have no idea why. Whenever you introduce
    # query parameters to the base url and pass them to stackalytics - you get
    # a 404 regardless. If you just use the base url
    # (http://stackalytics.com/api/1.0/stats/engineers) you'll get a successful
    # response from the stackalytics API. So, my hack-tastic workaround it to
    # get the base url and do my own "query parameter filtering" client-side
    # :(
    # url = 'http://stackalytics.com/api/1.0/stats/engineers'
    # params = {'user_id': 'ldbragst', 'project_type': 'keystone'}
    # resp = requests.get(url, params=params, allow_redirects=False)
    # resp = requests.get(url)
    # resp.raise_for_status()

    utc_today = datetime.datetime.utcnow()
    delta = datetime.timedelta(days=args.reporting_period)
    week_ago = utc_today - delta
    epoch_dt = datetime.datetime(1970, 1, 1)
    today_epoch = int((utc_today - epoch_dt).total_seconds())
    week_ago_epoch = int((week_ago - epoch_dt).total_seconds())

    url = 'http://stackalytics.com/api/1.0/stats/engineers'
    params = {'start_date': week_ago_epoch, 'end_date': today_epoch}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    engineering_data = resp.json()['stats']
    osic_report = dict()
    for engineer in engineering_data:
        for lp_id in LAUNCHPAD_IDS:
            if lp_id in engineer['id']:
                osic_report[engineer['id']] = engineer

    total_reviews = 0
    total_engineers = 0
    for engineer in osic_report:
        total_engineers += 1
        total_reviews += osic_report[engineer].get('metric')

    print(
        '%(e)d engineers did %(r)d code reviews in the last %(days)d days' % {
            'e': total_engineers,
            'days': args.reporting_period,
            'r': total_reviews})


if __name__ == '__main__':
    main()
