"""
hooks.registrations
This module defines functions to add link relations to registrations.
"""
import json
from log_trace.decorators import trace


@trace
def add_hooks(app):
    """Wire up the hooks for registrations."""
    app.on_fetched_item_registrations += _add_links_to_registration
    app.on_fetched_resource_registrations += _add_links_to_registrations_collection
    app.on_post_POST_registrations += _post_registrations
    app.on_pre_POST_registrations += _before_insert_registrations


@trace
def _before_insert_registrations(request):
    data = json.loads(request.get_data())
    data['rels'].pop('self')
    request._cached_data = json.dumps(data).encode('utf-8')


@trace
def _post_registrations(request, payload):
    if payload.status_code == 201:
        j = json.loads(payload.data)
        if '_items' in j:
            for registration in j['_items']:
                _add_links_to_registration(registration)
        else:
            _add_links_to_registration(j)
        payload.data = json.dumps(j)


@trace
def _add_links_to_registrations_collection(registrations_collection):
    for registration in registrations_collection['_items']:
        _add_links_to_registration(registration)


@trace
def _add_links_to_registration(registration):
    registration['_links']['self'] = {
        'href': f"/registrations/{registration['_id']}",
        'title': 'registration'
    }
