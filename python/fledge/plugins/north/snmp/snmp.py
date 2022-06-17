"""
Receives info from the south plugin systeminfo and
sends them as traps to an SNMP manager using:
for v2:
snmptrap -v <snmp_version> -c <community> <destination_host> <uptime> <OID_or_MIB> <object> <value_type> <value>
ex: snmptrap -v2c -c public 127.0.0.1:1163 12345 1.3.6.1.4.1.20408.4.1.1.2
for v3:
snmptrap -v <snmp_version> -e <engine_id> -u <security_username> -a <authentication_protocal> -A <authentication_protocal_pass_phrase> -x <privacy_protocol> -X <privacy_protocol_pass_phrase> -l authPriv <destination_host> <uptime> <OID_or_MIB> <object> <value_type> <value>
"""
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" SNMP North plugin"""

import asyncio
import json
import os

from itertools import chain

from attr import s

from fledge.common import logger
from fledge.plugins.common import *

__author__ = "Archer Jade"
__copyright__ = "Copyright (c) 2022, RTE (https://www.rte-france.com)"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

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
        'displayName': 'Manager address:port'
    },
    'snmpVersion': {
        'description': 'SNMP Version. Either v2c or v3.',
        "type": "enumeration",
        "default": "v2c",
        "options": ["v2c","v3"],
        'order': '2',
        'displayName': 'SNMP Version'
    },
    'EngID': {
        'description': 'Engine ID if using SNMPv3.',
        "type": "string",
        "default": "",
        'order': '3',
        'displayName': 'Engine ID (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    'Security': {
        'description': 'Security level if using SNMPv3.',
        "type": "enumeration",
        "default": "noAuthNoPriv",
        "options": ["noAuthNoPriv","authNoPriv","authPriv"],
        'order': '4',
        'displayName': 'Security level (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    'User': {
        'description': 'User name if using SNMPv3.',
        "type": "string",
        "default": "snmp3user",
        'order': '4',
        'displayName': 'User name (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    'AuthType': {
        'description': 'Authentification type if using SNMPv3.',
        "type": "enumeration",
        "default": "SHA",
        "options": ["SHA","MD5"],
        'order': '6',
        'displayName': 'Authentification type (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    'pwd': {
        'description': 'Password if using SNMPv3.',
        "type": "string",
        "default": "default",
        'order': '5',
        'displayName': 'Password (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    'EncType': {
        'description': 'Encryption type if using SNMPv3.',
        "type": "enumeration",
        "default": "AES",
        "options": ["AES","DES"],
        'order': '6',
        'displayName': 'Encryption type (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    'EncPwd': {
        'description': 'Password for encryption if using SNMPv3.',
        "type": "string",
        "default": "default",
        'order': '6',
        'displayName': 'PrivPassword (SNMPv3)',
        "validity": "snmpVersion == \"v3\""
    },
    "source": {
         "description": "Source of data to be sent on the stream. May be either readings or statistics.",
         "type": "enumeration",
         "default": "readings",
         "options": ["readings"],
         'order': '7',
         'displayName': 'Source'
    },
    "applyFilter": {
        "description": "Should filter be applied before processing data",
        "type": "boolean",
        "default": "false",
        'order': '8',
        'displayName': 'Apply Filter'
    },
    "filterRule": {
        "description": "JQ formatted filter to apply (only applicable if applyFilter is True)",
        "type": "string",
        "default": ".[]",
        'order': '9',
        'displayName': 'Filter Rule',
        "validity": "applyFilter == \"true\""
    }
}

_LOGGER = logger.setup(__name__, level=logger.logging.INFO)

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
    _LOGGER.info('snmp plugin started.')
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
    _LOGGER.info('snmp plugin shut down.')


class SNMPnorth(object):
    """ North SNMP Plugin """

    def __init__(self):
        #self.event_loop = asyncio.get_event_loop()
        pass
    def send_trap(self,snmp_server, oid, value):
        
        if type(value)==str:
            t = "s"
        else:
            t="i"
        if config["snmpVersion"]["value"]== "v2c":
            #OID .1.3.6.1.6.3.1.1.4.1: The authoritative identification of the notification
            #currently being sent.  This variable occurs as
            #the second varbind in every SNMPv2-Trap-PDU and
            #InformRequest-PDU.
            os.system("snmptrap -v2c -c public {} '' {} 1.3.6.1.6.3.1.1.4.1 {} \"{}\"".format(snmp_server, oid, t, value))
        else: #SNMPv3
            if config["Security"]["value"] == "noAuthNoPriv":
                os.system("snmptrap -v 3 -e {} -u {} -l {} {} '' .{} .{}.1.1.1.1.1 {} {}".format(config["EngID"]["value"],config["User"]["value"],config["AuthType"]["value"], config["pwd"]["value"],config["Security"]["value"],snmp_server,oid, oid, t, value))
            elif config["Security"]["value"] == "AuthNoPriv":
                os.system("snmptrap -v 3 -e {} -u {} -a {} -A {} -l {} {} '' .{} .{}.1.1.1.1.1 {} {}".format(config["EngID"]["value"],config["User"]["value"],config["AuthType"]["value"], config["pwd"]["value"],config["Security"]["value"],snmp_server,oid, oid, t, value))
            else:
                s = ("snmptrap -v 3 -e {} -u {} -a {} -A {} -x {} -X {} -l {} {} '' .{} .{}.1.1.1.1.1 {} {}".format(config["EngID"]["value"],config["User"]["value"],config["AuthType"]["value"], config["pwd"]["value"],config["EncType"]["value"],config["EncPwd"]["value"],config["Security"]["value"],snmp_server,oid, oid, t, value))
                os.system("snmptrap -v 3 -e {} -u {} -a {} -A {} -x {} -X {} -l {} {} '' .{} .{}.1.1.1.1.1 {} {}".format(config["EngID"]["value"],config["User"]["value"],config["AuthType"]["value"], config["pwd"]["value"],config["EncType"]["value"],config["EncPwd"]["value"],config["Security"]["value"],snmp_server,oid, oid, t, value))
                _LOGGER.info(s)

    def get_OID(self, reading):
        # Dictionary pairing oid with systeminfo names
        f = {
            "cpuUsage_All": {
                "prcntg_usr": "1.3.6.1.4.1.2021.11.50",
                "prcntg_nice": "1.3.6.1.4.1.2021.11.51",
                "prcntg_sys": "1.3.6.1.4.1.2021.11.52",
                "prcntg_iowait": "1.3.6.1.4.1.2021.11.54",
                "prcntg_irq": "1.3.6.1.4.1.2021.11.56",
                "prcntg_soft": "1.3.6.1.4.1.2021.11.61",
                "prcntg_steal": "1.3.6.1.4.1.2021.11.64",
                "prcntg_guest": "1.3.6.1.4.1.2021.11.65",
                "prcntg_gnice": "1.3.6.1.4.1.2021.11.66",
                "prcntg_idle": "1.3.6.1.4.1.2021.11.53"
            },
            "hostName": "1.3.6.1.4.1.9.2.1.3",
            "memInfo":{
                "MemTotal_KB": "1.3.6.1.4.1.2021.4.5",
                "MemFree_KB": "1.3.6.1.4.1.2021.4.11",
                "MemAvailable_KB": "1.3.6.1.4.1.2021.4.6",
                "Buffers_KB": "1.3.6.1.4.1.2021.4.14",
                "Cached_KB": "1.3.6.1.4.1.2021.4.15",
                "SwapFree_KB": "1.3.6.1.4.1.2021.4.4",
                "SwapTotal_KB": "1.3.6.1.4.1.2021.4.3"
            },
            "pagingAndSwappingEvents":{
                "swappedin": "1.3.6.1.4.1.2021.11.62",
                "swappedout": "1.3.6.1.4.1.2021.11.63",
                "pagedin": "1.3.6.1.4.1.546.1.1.8.8.22",
                "pageout":"1.3.6.1.4.1.546.1.1.8.8.23"
            },
            "uptime ":{
                "system_seconds": "1.3.6.1.2.1.1.3.0"
            },
            "loadAverage":{
                "overLast15mins": "1.3.6.1.4.1.2021.10.1.3.3",
                "overLast1min": "1.3.6.1.4.1.2021.10.1.3.1",
                "overLast5mins": "1.3.6.1.4.1.2021.10.1.3.2"
            },
            "processes":{
                "running": "1.3.6.2.1.25.1.6",
                "zombie": "1.3.6.1.4.1.546.1.1.7.8.34",
                "sleep": "1.3.6.1.4.1.546.1.1.7.8.8"
            }
        }

        # Iterating through the json
        # list

        _LOGGER.info('readings: ', reading)
        oid = self.find_values(reading, f)

        return oid

    def find_values(self, id, json_repr):
        results = []

        def _decode_dict(a_dict):
            try:
                results.append(a_dict[id])
            except KeyError:
                pass
            return a_dict
        json_repr=json.dumps(json_repr)
        json.loads(json_repr, object_hook=_decode_dict) # Return value ignored.
        return results

    def _get_OID(self, dict):
        jsonData = dict
        names = []

        try: #nested case
            oid = []
            foo = str(*jsonData.keys())
            newdic=jsonData[foo]
            for k,v in jsonData.items():
                names.append(v.keys())
            for n1 in names:
                for n2 in list(n1):
                    oid=(self.get_OID(n2))
                    newdic[oid[0]]=newdic.pop(n2)
            return newdic
        except: #non nested case
            if jsonData == {}:
                _LOGGER.info('empty!')
            else:
                names=list(jsonData.keys())
                print(names)
                for n1 in names:
                    n2=n1
                    oid = self.get_OID(n2)
                    try:
                        jsonData[oid[0]]=jsonData.pop(n2)
                    except:
                        pass
        #_LOGGER.info(jsonData)
        return jsonData


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
                    read["reading"] = self._get_OID(p['reading'])
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
        val = {'reading': {}}
        l=payload_block
        l = [i for i in l if i != val]
        print(l)
        for n in l:
            tmp_payload=n["reading"]
            names=list(tmp_payload.keys())
            for n1 in names:
                oid=str(n1)
                value=tmp_payload.get(n1)
                try:
                    value=int(tmp_payload.get(n1))
                except:
                    value=str(tmp_payload.get(n1))
                try:
                    self.send_trap(config["destination"]["value"], oid, value)
                except Exception as ex:
                    _LOGGER.exception(f'Exception sending payloads: {ex}')
        else:
            num_count += len(payload_block)
        return num_count

    async def _send(self, payload):
        """ Send the payload, using provided manager """

        #await client.send_message(message)
        _LOGGER.info('Message successfully sent')