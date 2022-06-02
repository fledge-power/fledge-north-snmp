"""
Envoie un poll de façon périodique au plugin sud, envoie plusieurs:
Récupère les valeurs et envoie un trap:
snmptrap -v <snmp_version> -c <community> <destination_host> <uptime> <OID_or_MIB> <object> <value_type> <value>
ex: snmptrap -v2c -c public 127.0.0.1:1163 12345 1.3.6.1.4.1.20408.4.1.1.2
pour la v3: !pas encore fait
snmptrap -v <snmp_version> -e <engine_id> -u <security_username> -a <authentication_protocal> -A <authentication_protocal_pass_phrase> -x <privacy_protocol> -X <privacy_protocol_pass_phrase> -l authPriv <destination_host> <uptime> <OID_or_MIB> <object> <value_type> <value>

"""
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" SNMP North plugin"""

import asyncio
import json
from asyncio.log import logger
import json
import os
from itertools import chain

from fledge.common import logger
from fledge.plugins.north.common.common import *

__author__ = "Archer Jade"
__copyright__ = "Copyright (c) 2022, RTE (https://www.rte-france.com)"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


SNMPnorth = None
config = ""

_CONFIG_CATEGORY_NAME = "SNMPAGENT"
_CONFIG_CATEGORY_DESCRIPTION = "SNMP North Plugin"

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'SNMP North Plugin',
         'type': 'string',
         'default': 'snmp',
         'readonly': 'true'
    },
    'destination': {
        'description': 'Destination Manager that will receive the traps',
        'type': 'string',
        'default': 'localhost:1162',
        'order': '1',
        'displayName': 'destManager'
    },
    'snmpVersion': {
        'description': 'SNMP Version. Either v2c or v3.',
        "type": "enumeration",
        "default": "v2c",
        "options": ["v2c","v3"],
        'order': '2',
        'displayName': 'snmpVersion'
    },
    "source": {
         "description": "Source of data to be sent on the stream. May be either readings or statistics.",
         "type": "enumeration",
         "default": "readings",
         "options": ["readings"],
         'order': '3',
         'displayName': 'Source'
    },
    "applyFilter": {
        "description": "Should filter be applied before processing data",
        "type": "boolean",
        "default": "false",
        'order': '4',
        'displayName': 'Apply Filter'
    },
    "filterRule": {
        "description": "JQ formatted filter to apply (only applicable if applyFilter is True)",
        "type": "string",
        "default": ".[]",
        'order': '5',
        'displayName': 'Filter Rule',
        "validity": "applyFilter == \"true\""
    }
}




def plugin_info():
    """ Used only once when call will be made to a plugin.

        Args:
        Returns:
            Information about the plugin including the configuration for the plugin
    """
    return {
        'name': 'snmp',
        'version': '1.9.2',
        'type': 'north',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(data):
    """ Used for initialization of a plugin.

    Args:
        data - Plugin configuration
    Returns:
        Dictionary of a Plugin configuration
    """
    global SNMPnorth, config
    SNMPnorth = SNMPnorth()
    config = data
    return config

async def plugin_send(handle, payload, stream_id):
    """ Used to send the readings block from north to the configured destination.

    Args:
        handle - An object which is returned by plugin_init
        payload - A List of readings block
        stream_id - An Integer that uniquely identifies the connection from Fledge instance to the destination system
    Returns:
        Tuple which consists of
        - A Boolean that indicates if any data has been sent
        - The object id of the last reading which has been sent
        - Total number of readings which has been sent to the configured destination
    """
    try:
        is_data_sent, new_last_object_id, num_sent = await SNMPnorth.send_payloads(payload)
    except asyncio.CancelledError:
        pass
    else:
        return is_data_sent, new_last_object_id, num_sent

def plugin_shutdown(handle):
    """ Used when plugin is no longer required and will be final call to shutdown the plugin. It should do any necessary cleanup if required.

    Args:
         handle - Plugin handle which is returned by plugin_init
    Returns:
    """


class SNMPnorth(object):
    """ North SNMP Plugin """

    def __init__(self):
        #self.event_loop = asyncio.get_event_loop()
        pass
    def send_trap(self,snmp_server, oid, value):
        os.system("snmptrap -v2c -c public {} '' {} {} {}".format(snmp_server, oid, type(value), value))
    
    def get_OID(self, reading):
        # Opening JSON file
        f = open('./name_assos.json')

        # Iterating through the json
        # list
        oid = self.find_values(reading.keys(), f)

        # Closing file
        f.close()

        return oid

    def _get_OID(self, dict):
        jsonData = dict["reading"]
        names = []
        oid = []
        try:
            for k,v in jsonData.items():
                names.append(v.keys())
            for n1 in names:
                for n2 in list(n1):
                    oid.append(self.get_OID(n2))
        except:
            names=list(jsonData.keys())
            for n1 in names:
                oid.append(self.get_OID(n1))
                
        oids=list(chain(*oid))

        return oids
    
    def find_values(id, json_repr):
        results = []

        def _decode_dict(a_dict):
            try:
                results.append(a_dict[id])
            except KeyError:
                pass
            return a_dict

        json.loads(json_repr.read(), object_hook=_decode_dict) # Return value ignored.
        return results


    
    async def send_payloads(self, payloads):
        is_data_sent = False
        last_object_id = 0
        num_sent = 0

        try:
            _LOGGER.info('processing payloads')
            payload_block = list()

            for p in payloads:
                if "system" in p['asset_code']:
                    #only add the readings from systeminfo plugin
                    last_object_id = p["id"]
                    read = dict()
                    read["value"] = p['reading'].value()
                    read["oid"]=self._get_OID(p['reading'])
                    payload_block.append(read)

            num_sent = await self._send_payloads(payload_block)
            _LOGGER.info('payloads sent: {num_sent}')
            is_data_sent = True
        except Exception as ex:
            _LOGGER.exception("Data could not be sent, %s", str(ex))

        return is_data_sent, last_object_id, num_sent
    
    async def _send_payloads(self, payload_block):
        """ send a list of block payloads"""
        num_count = 0
        try:
            self.send_trap(config["snmp_server"]["value"], payload_block["oid"], payload_block["value"] )
        except Exception as ex:
            _LOGGER.exception(f'Exception sending payloads: {ex}')
        else: 
            num_count += len(payload_block)
        return num_count

    async def _send(self, payload):
        """ Send the payload, using provided manager """

        #await client.send_message(message)
        _LOGGER.info('Message successfully sent')