"""
Defines the resources that comprise the eve-service-gateway domain.
"""
from . import _settings
from . import registrations


DOMAIN_DEFINITIONS = {
    '_settings': _settings.DEFINITION,
    'registrations': registrations.DEFINITION
}


DOMAIN_RELATIONS = {
}


DOMAIN = {**DOMAIN_DEFINITIONS, **DOMAIN_RELATIONS}
