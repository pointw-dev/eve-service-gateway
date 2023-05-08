import logging
import json
from utils import echo_message, get_db
import hooks._error_handlers
import hooks._settings
import hooks._logs
from log_trace.decorators import trace
from configuration import SETTINGS, SETTINGS_GATEWAY
import hooks.registrations
import hashlib

LOG = logging.getLogger('hooks')


class EtagException(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


@trace
def add_hooks(app):
    app.on_post_GET += _fix_links
    app.on_post_POST += _post_POST
    app.on_post_PATCH += _fix_links

    if SETTINGS.is_enabled('ES_ADD_ECHO'):
        @app.route('/_echo', methods=['PUT'])
        def _echo_message():
            return echo_message()

    hooks._error_handlers.add_hooks(app)
    hooks._settings.add_hooks(app)
    hooks._logs.add_hooks(app)
    hooks.registrations.add_hooks(app)



@trace
def _post_POST(resource, request, payload):
    if payload.status_code == 201:
        j = json.loads(payload.data)
        if '_items' in j:
            for item in j['_items']:
                _remove_unnecessary_links(item)
        else:
            _remove_unnecessary_links(j)

        if 'pretty' in request.args:
            payload.data = json.dumps(j, indent=4)
        else:
            payload.data = json.dumps(j)


@trace
def _fix_links(resource, request, payload):
    if payload.status_code in [200, 201]:
        j = json.loads(payload.data)

        if resource is None:
            try:
                _handle_schema_request(j, payload, request)
            except EtagException as ex:
                payload.status_code = ex.status_code
                payload.data = b''
                return
        else:
            if '_items' in j:
                for item in j['_items']:
                    _process_item_links(item)
            else:
                _add_parent_link(j, resource)
            _process_item_links(j)

        payload.data = json.dumps(j, indent=4 if 'pretty' in request.args else None)


def _handle_schema_request(j, payload, request):
    etag = _rewrite_schema_links(j)
    payload.headers.add_header('Etag', etag)
    j['_etag'] = etag

    if_none_match_header = request.headers.get('if-none-match', '')
    if_match_header = request.headers.get('if-match', '')

    if if_none_match_header == '*' or etag in if_none_match_header:
        raise EtagException(304)
    if etag not in if_match_header:
        raise EtagException(412)


@trace
def _process_item_links(item):
    _remove_unnecessary_links(item)
    _add_missing_slashes(item)
    _insert_base_url(item)


@trace
def _rewrite_schema_links(item):
    base_url = SETTINGS.get('ES_BASE_URL') or ''

    if '_links' in item and 'child' in item['_links'] and len(item['_links']) == 1:
        old = item['_links']['child']
        del item['_links']['child']
        new_links = _create_new_schema_links(base_url, old)
        item['_links'] = new_links

    _create_gateway_links(item)
    return hashlib.md5(json.dumps(item['_links']).encode('utf-8')).hexdigest()


@trace
def _create_new_schema_links(base_url, old_links):
    new_links = {
        'self': {'href': f'{base_url}/', 'title': 'endpoints'},
        'logging': {'href': f'{base_url}/_logging', 'title': 'logging'}
    }

    for link in old_links:
        if '<' not in link['href'] and not link['title'] == '_schema':
            rel = link['title'][1:] if link['title'].startswith('_') else link['title']
            link['href'] = f'{base_url}/{link["href"]}'
            new_links[rel] = link

    return new_links


@trace
def _remove_unnecessary_links(item):
    if 'related' in item.get('_links', {}):
        del item['_links']['related']


@trace
def _add_missing_slashes(item):
    if '_links' not in item:
        return
    for link in item['_links'].values():
        href = link.get('href')
        if href and not (href.startswith('/') or href.startswith('http://') or href.startswith('https://')):
            link['href'] = '/' + href


@trace
def _insert_base_url(item):
    if '_links' not in item:
        return
    base_url = SETTINGS.get('ES_BASE_URL') or ''
    for link in item['_links'].values():
        if link['href'].startswith('/'):
            link['href'] = f'{base_url}{link["href"]}'


@trace
def _add_parent_link(item, resource):
    item['_links']['parent'] = {
        'href': item['_links']['collection']['href'],
        'title': resource
    }


@trace
def _create_gateway_links(j):
    db = get_db()
    registration_col = db["registrations"]
    curies = []
    all_links = dict()
    for record in registration_col.find():
        _append_base_url(record)
        for key, value in record["rels"].items():
            if registration_col.count_documents({"$and": [{f"rels.{key}": {'$exists': 1}}, {'name': {"$ne": record["name"]}}]}) or j["_links"].get(f"{key}") != None:
                all_links[record["name"] + ":" + key] = record["rels"][key]
            else:
                all_links[key] = record["rels"][key]
            curie_instance = dict()
            curie_instance["name"] = record["name"]
            curie_instance["href"] = (
                SETTINGS_GATEWAY.get("GW_CURIES_BASE_URL", "")
                + f'/{record["name"]}/relations/{"{rel}"}'
            )
            curie_instance["templated"] = True
            if curie_instance not in curies:
                curies.append(curie_instance)
    j = {"_links": all_links | j["_links"]}
    if curies:
        j["_links"]["curies"] = curies
    return j


@trace
def _append_base_url(registration_instance):
    for key, value in registration_instance["rels"].items():
        value["href"] = registration_instance["baseUrl"] + value["href"]

