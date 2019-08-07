import logging
import json
import requests

from ...core.events import handler
from ...core.events.types import Vulnerability, Event
from ...core.types import Hunter, ActiveHunter, KubernetesCluster, RemoteCodeExec, AccessRisk, InformationDisclosure, \
    PrivilegeEscalation, DenialOfService
from .apiserver import K8sVersionDisclosure

""" Vulnerabilities """


class ServerApiVersionEndPointAccessPE(Vulnerability, Event):
    """Node is vulnerable to critical CVE-2018-1002105"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Critical Privilege Escalation CVE", category=PrivilegeEscalation)
        self.evidence = evidence


class ServerApiVersionEndPointAccessDos(Vulnerability, Event):
    """Node not patched for CVE-2019-1002100. Depending on your RBAC settings, a crafted json-patch could cause a Denial of Service."""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Denial of Service to Kubernetes API Server", category=DenialOfService)
        self.evidence = evidence


# Passive Hunter
@handler.subscribe(K8sVersionDisclosure)
class IsVulnerableToCVEAttack(Hunter):
    """CVE hunter
    Checks if Node is running a Kubernetes version vulnerable to critical CVEs
    """

    def __init__(self, event):
        self.event = event
        self.api_server_evidence = ''
        self.k8sVersion = ''

    def parse_api_server_version_end_point(self):
        try:
            self.api_server_evidence = self.event.version
            resDict = json.loads(self.event.version)
            version = resDict["gitVersion"].split('.')
            first_two_minor_digits = int(version[1])
            last_two_minor_digits = int(version[2])
            logging.debug('Passive Hunter got version from the API server version end point: %d.%d', first_two_minor_digits, last_two_minor_digits)
            return [first_two_minor_digits, last_two_minor_digits]

        except (requests.exceptions.ConnectionError, KeyError):
            return None

    def check_cve_2018_1002105(self, api_version):
        first_two_minor_digists = api_version[0]
        last_two_minor_digists = api_version[1]

        if first_two_minor_digists == 10 and last_two_minor_digists < 11:
            return True
        elif first_two_minor_digists == 11 and last_two_minor_digists < 5:
            return True
        elif first_two_minor_digists == 12 and last_two_minor_digists < 3:
            return True
        elif first_two_minor_digists < 10:
            return True

        return False

    def check_cve_2019_1002100(self, api_version):
        """
        Kubernetes v1.0.x-1.10.x
        Kubernetes v1.11.0-1.11.7 (fixed in v1.11.8)
        Kubernetes v1.12.0-1.12.5 (fixed in v1.12.6)
        Kubernetes v1.13.0-1.13.3 (fixed in v1.13.4)
        """

        first_two_minor_digists = api_version[0]
        last_two_minor_digists = api_version[1]

        if first_two_minor_digists == 11 and last_two_minor_digists < 8:
            return True
        elif first_two_minor_digists == 12 and last_two_minor_digists < 6:
            return True
        elif first_two_minor_digists == 13 and last_two_minor_digists < 4:
            return True
        elif first_two_minor_digists < 11:
            return True

        return False

    def execute(self):
        api_version = self.parse_api_server_version_end_point()

        if api_version:
            if self.check_cve_2018_1002105(api_version):
                self.publish_event(ServerApiVersionEndPointAccessPE(self.api_server_evidence))

            if self.check_cve_2019_1002100(api_version):
                self.publish_event(ServerApiVersionEndPointAccessDos(self.api_server_evidence))


