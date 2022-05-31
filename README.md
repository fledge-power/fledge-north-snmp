# fledge-north-snmp

The ability to monitor the gateway in real time is a key feature for any organization that manages a power system telecontrol network. This feature is part of the supervision and incident management system.
Simple Network Management Protocol (SNMP) is an application–layer protocol defined by the Internet Architecture Board (IAB) in RFC1157 for exchanging management information between network devices.
SNMP is one of the widely accepted network protocols to manage and monitor network elements. Most of the professional–grade network elements come with bundled SNMP agent. These agents have to be enabled and configured to communicate with the network monitoring tools or network management system (NMS).

SNMP agent north plugin converts the collected data stream to SNMP notifications (traps or informs) and send them to the remote SNMP manager (server.)

## Installation

1) Copy the python/fledge/plugins/north/snmp directory to /usr/local/fledge/python/fledge/python/plugins/north/

## Testing

