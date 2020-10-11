#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" iCal to KNX Gateway

This program implements a gateway that fetches an iCal URL, parses for events
and will send values based on triggers that define an offset to an event.


This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Andreas Thienemann"
__contact__ = "andreas@thienemann.net"
__copyright__ = "Copyright 2020, Andreas Thienemann"
__date__ = "2020/10/09"
__deprecated__ = False
__license__ = "GPLv3+"
__maintainer__ = "developer"
__status__ = "Production"
__version__ = "1.0.0"

import asyncio
import configparser
from xknx import XKNX
from xknx.devices import ExposeSensor
from xknx.io import ConnectionConfig, ConnectionType
from xknx.io.const import DEFAULT_MCAST_PORT
from icalevents.icalevents import events
import os
import sys
import logging
import pickle
import click
from datetime import datetime, timedelta
from dateutil.tz import UTC
from pprint import pprint


class knxcal:
    def __init__(self):
        self.cwd = os.path.dirname(__file__)
        self._load_config()
        self.busaccess = True
        self.statekeeping = True

    def _load_config(self, filename="knxcal.ini"):
        """ Load the knxcal configuration from a file. """
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(os.path.join(self.cwd, filename))
        try:
            self.calUrl = self.config["knxcal"]["iCalURL"]
            self.match = self.config["knxcal"]["eventName"]
            self.statefile = os.path.join(self.cwd, self.config["knxcal"]["stateFile"])
        except (KeyError, AttributeError):
            logging.critical("Error reading config.")
            sys.exit(225)

    def _fetch_ical(self):
        """ Fetch and parse the iCal URL"""
        starttime = datetime.now(UTC) - timedelta(days=2)
        self.events = events(self.calUrl, start=starttime)
        logging.debug(self.events)

    def send_if_new(self, ga, dpt, value, trigger, event):
        """Send data to the bus if we have not done so before.
        Keep state of notifications for events to prevent repeats."""
        if self.statekeeping:
            try:
                with open(self.statefile, "rb") as f:
                    state = pickle.load(f)
                    self.expire_state(state)
            except IOError:
                state = {}
        else:
            logging.warning("State disabled. Not loading state from file.")
            state = {}
        key = "{}_{}_{}_{}_{}".format(event.summary, event.start, event.end, ga, value)
        if key in state:
            logging.info("Already notified for %s, skipping.", event)
            return
        logging.info("Notifying for %s.", event)
        self.send_to_ga(ga, dpt, value)
        state.update(
            {key: {"notifytime": datetime.now(), "trigger": trigger, "event": event}}
        )
        if self.statekeeping:
            with open(self.statefile, "wb") as f:
                pickle.dump(state, f)
        else:
            logging.warning("State disabled. Not saving state to file.")

    def expire_state(self, state):
        """ Expire events that are 7 days in the past """
        expire = []
        for name, data in state.items():
            if (data["event"].end - datetime.now(UTC)).total_seconds() / 60 / 60 < -(
                24 * 7
            ):
                expire.append(name)
        for name in expire:
            logging.debug("Expiring %s", name)
            del state[name]
        return state

    def send_to_ga(self, ga, dpt, value):
        """ Connect to the KNX bus and set a value. """
        if not self.busaccess:
            logging.warning(
                "Busaccess disabled, not sending val(%s) to ga(%s)", value, ga
            )
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        xknx = XKNX()
        if "connection" in self.config:
            connection_types = {
                "tunneling": ConnectionType.TUNNELING,
                "routing": ConnectionType.ROUTING,
                "auto": ConnectionType.AUTOMATIC,
            }
            connection_config = ConnectionConfig(
                connection_type=connection_types[
                    self.config["connection"].get("type", "auto")
                ],
                gateway_ip=self.config["connection"].get("gateway_ip", None),
                gateway_port=self.config["connection"].get(
                    "gateway_port", DEFAULT_MCAST_PORT
                ),
                local_ip=self.config["connection"].get("local_ip", None),
                auto_reconnect=self.config["connection"].get("autoReconnect", True),
            )
            logging.debug("Applying custom connection config %s", connection_config)
            xknx.connection_config = connection_config
        loop.run_until_complete(xknx.start())
        expose_sensor = ExposeSensor(
            xknx, "CalendarSensor", group_address=ga, value_type=dpt
        )
        logging.info("Sending val(%s) to ga(%s)", value, ga)
        loop.run_until_complete(expose_sensor.set(value))
        logging.debug(expose_sensor)
        loop.run_until_complete(xknx.stop())

    def find_trigger(self, event):
        """ Run triggers and see what we need to notify for """
        ga, dtp, value = (None, None, None)
        for section in sorted(
            self.config.sections(),
            reverse=True,
            key=lambda x: int(self.config[x].get("offset", 0)),
        ):
            if not section.startswith("trigger"):
                logging.debug(
                    "Skipping section %s, name not starting with trigger", section
                )
                continue
            trigger = self.config[section]
            offset = int(trigger["offset"])
            base = trigger["base"]
            if base == "begin":
                timediff = event.start - datetime.now(UTC)
            elif base == "end":
                timediff = event.end - datetime.now(UTC)
            else:
                raise RuntimeError(
                    """Trigger base needs to be either "begin" or "end", not {}""".format(
                        base
                    )
                )
            event_hours_offset = int(timediff.total_seconds() / 60 / 60)
            logging.debug(
                "Event %s with offset %s and base %s comparing at event_hours_offset %s/%s to event",
                event.summary,
                offset,
                base,
                event_hours_offset,
                timediff.total_seconds(),
            )
            if event_hours_offset <= offset:
                logging.debug("Trigger %s/%s matched for %s", trigger, offset, event)
                match = section
                ga = trigger["address"]
                dtp = trigger["dtp"]
                value = trigger["value"]
        if ga:
            return {"section": match, "ga": ga, "dtp": dtp, "value": value}
        logging.debug("No trigger matched.")
        return False

    def run(self):
        """ Main executor """
        self._fetch_ical()
        if len(self.events) == 0:
            logging.warning("No events found within the next days.")
        for event in self.events:
            if event.summary == self.match:
                trigger = self.find_trigger(event)
                if trigger:
                    logging.debug("Triggered %s for %s", trigger["section"], event)
                    self.send_if_new(
                        trigger["ga"], trigger["dtp"], trigger["value"], trigger, event
                    )


@click.command()
@click.option("--debug", is_flag=True, help="Debug output")
@click.option("--no-knx", is_flag=True, default=False, help="Disable KNX bus access")
@click.option("--no-state", is_flag=True, default=False, help="Disable state keeping")
@click.option("--log", type=click.Path(dir_okay=False), help="Log to file FILE")
def main(debug, no_knx, no_state, log):
    """iCal to KNX Gateway

    This program implements a gateway that fetches an iCal URL, parses for events
    and will send values based on triggers that define an offset to an event."""
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    if log:
        format = "%(asctime)s %(levelname)s:%(name)s:%(message)s"
        logfile = log
        handlers = (
            [
                logging.handlers.RotatingFileHandler(
                    logfile, maxBytes=1000000, backupCount=4
                )
            ],
        )
    else:
        format = "%(levelname)s:%(name)s:%(message)s"
        handlers = [logging.StreamHandler()]
        logfile = None

    logging.basicConfig(
        format=format,
        level=level,
        filename=logfile,
    )

    def exception_hook(exc_type, exc_value, exc_traceback):
        logging.critical(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = exception_hook

    logging.info("KNX Calendar Gateway v%s", __version__)
    c = knxcal()
    c.busaccess = not no_knx
    c.statekeeping = not no_state
    c.run()


if __name__ == "__main__":
    main()
