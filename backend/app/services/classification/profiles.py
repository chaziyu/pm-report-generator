"""
Category classification profiles for FortiGate PM screenshot classification V2.
Structured semantic profiles distinguishing:
- strong_anchors: Highly specific semantic markers
- strong_groups: Semantic multi-token co-occurrence groups
- supporting_anchors: Corroborating contextual evidence
- weak_anchors: Generic contextual terms (never alone produce high confidence)
- negative_anchors: Explicit counter-evidence
- url_anchors: High-specificity URL/web path evidence
- regex_patterns: Structural/format regex patterns
- navigation_terms: Sidebar and top navigation terms that must not dominate scoring
"""

from typing import Dict, Any

CATEGORY_PROFILES: Dict[str, Dict[str, Any]] = {
    "cpu_usage": {
        "strong_anchors": [
            "cpu", "cpu utilization", "processor", "cpu usage", "cpu load", "cpu %",
            "cpu utilization (last", "cpu core", "cpu history"
        ],
        "strong_groups": [
            ["cpu", "%"],
            ["cpu", "utilization"],
            ["cpu", "usage"],
            ["processor", "%"],
            ["cpu", "current usage"],
            ["cpu", "core"],
        ],
        "supporting_anchors": [
            "current usage", "cores", "utilization", "last 24 hours", "last 12 hours",
            "last 60 minutes", "utilization:", "average:", "peak:"
        ],
        "weak_anchors": ["usage", "%", "load"],
        "negative_anchors": [
            "memory", "ram", "memory utilization", "mem usage", "shared memory", "ram utilization"
        ],
        "url_anchors": [],
        "regex_patterns": [
            r"\bcpu\s*(?:utilization|usage|load)?[:\s]*\d+\s*%",
            r"\bcpu\s*utilization\b",
            r"\bcpu\s*load\b",
            r"\bprocessor\s*utilization\b",
            r"\bcpu\b.*\b\d+\s*%",
            r"\bcpu\b.*\bcurrent\s*usage\b",
        ],
        "navigation_terms": ["dashboard", "system", "status"],
        "requires_label_value": True,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "memory_usage": {
        "strong_anchors": [
            "memory", "mem", "ram", "memory utilization", "mem usage", "memory usage", "shared memory",
            "ram utilization", "memory %", "memory utilization (last", "active memory"
        ],
        "strong_groups": [
            ["memory", "%"],
            ["memory", "utilization"],
            ["memory", "usage"],
            ["ram", "%"],
            ["memory", "current usage"],
            ["memory", "allocated"],
        ],
        "supporting_anchors": [
            "current usage", "allocated", "free", "total memory", "active",
            "last 24 hours", "last 12 hours", "utilization:", "average:", "peak:"
        ],
        "weak_anchors": ["usage", "%", "allocated"],
        "negative_anchors": [
            "cpu", "processor", "cpu utilization", "cpu load", "processor usage", "cpu %"
        ],
        "url_anchors": [],
        "regex_patterns": [
            r"\bmem(?:ory)?\s*(?:utilization|usage)?[:\s]*\d+\s*%",
            r"\bshared\s*memory\b",
            r"\bactive\s*memory\b",
            r"\bmemory\s*utilization\b",
            r"\bmem(?:ory)?\b.*\b\d+\s*%",
            r"\bmem(?:ory)?\b.*\bcurrent\s*usage\b",
        ],
        "navigation_terms": ["dashboard", "system", "status"],
        "requires_label_value": True,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "interface": {
        "strong_anchors": [
            "physical interface", "link status", "aggregate interface", "vlan interface",
            "faceplate", "interface status", "virtual domain interface", "hardware switch",
            "software switch", "loopback interface"
        ],
        "strong_groups": [
            ["interface", "link status"],
            ["interface", "ip/netmask"],
            ["port", "link status"],
            ["port", "speed", "duplex"],
            ["interfaces", "port"],
            ["interface", "virtual domain"],
        ],
        "supporting_anchors": [
            "port", "dmz", "wan", "lan", "vlan", "ip/netmask", "speed", "duplex",
            "link status", "traffic in", "traffic out", "mac address", "interface name"
        ],
        "weak_anchors": ["network", "interface", "interfaces", "status"],
        "negative_anchors": [
            "system settings", "time zone", "system time", "/system/ha", "system/ha",
            "static route", "routing monitor", "destination", "gateway", "fib"
        ],
        "url_anchors": ["/ng/interface", "interface/"],
        "regex_patterns": [
            r"\bport\d+\b",
            r"\blink\s*status\b",
            r"\bip\/netmask\b",
            r"\bphysical\s+interfaces?\b",
            r"\bfortigate\s+\d+[a-z]?\s+(?:\d+\s*)+",
        ],
        "navigation_terms": ["network", "interfaces", "system"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "license_info": {
        "strong_anchors": [
            "licenses", "license", "forticare", "registration status", "contract number", "support contract",
            "support coverage", "device registration", "entitlement", "forticare support",
            "licenses & definitions", "license status", "fortitoken", "forti token"
        ],
        "strong_groups": [
            ["license", "forticare"],
            ["licenses", "fortitoken"],
            ["licenses", "web"],
            ["licenses", "antivirus"],
            ["licenses", "servers"],
            ["licenses", "rating"],
            ["license", "status"],
            ["registration", "status"],
            ["license", "support"],
            ["license", "valid"],
            ["license", "expiration"],
            ["licenses", "updates"],
        ],
        "supporting_anchors": [
            "antivirus", "ips", "web filter", "anti-spam", "support", "expiration",
            "valid", "registered", "unregistered", "servers", "rating", "entitlement",
            "fortitoken", "forti token", "outbreak prevention", "security rating"
        ],
        "weak_anchors": ["status"],
        "negative_anchors": [
            "/ng/system/fortiguard", "/system/fortiguard", "update licenses & definitions",
            "database version", "distribution network", "definitions & signatures",
            "av engine", "attack definition"
        ],
        "url_anchors": ["/ng/system/forticare", "/system/license"],
        "regex_patterns": [
            r"\bforticare\b",
            r"\bregistration\s*status\b",
            r"\bvalid\s*until\b",
            r"\bsupport\s*coverage\b",
        ],
        "navigation_terms": ["system", "dashboard", "status"],
        "requires_label_value": False,
        "base_weight": 0.65,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "firmware_version": {
        "strong_anchors": [
            "firmware version", "fortios", "current firmware", "firmware:",
            "firmware build", "active partition", "firmware mode", "active firmware", "new firmware version"
        ],
        "strong_groups": [
            ["firmware", "build"],
            ["firmware", "v7."],
            ["firmware", "v6."],
            ["firmware", "mature"],
            ["firmware", "feature"],
            ["fortios", "build"],
            ["fortios", "version"],
            ["system information", "firmware"],
        ],
        "supporting_anchors": [
            "firmware", "build", "mature", "feature", "v7.", "v6.", "upgrade",
            "backup", "serial number", "hostname", "system information"
        ],
        "weak_anchors": ["system", "version", "system information"],
        "negative_anchors": [
            "/ng/system/fortiguard", "/system/fortiguard", "fortiguard distribution",
            "attack definition", "av engine", "/ng/routing", "/system/dashboard"
        ],
        "url_anchors": ["/ng/system/firmware", "/system/firmware"],
        "regex_patterns": [
            r"\bv\d+\.\d+\.\d+\b",
            r"\bbuild\s*\d+\b",
            r"\bfortios\s*(?:v\d+|version)\b",
            r"\b(?:mature|feature)\s+branch\b",
            r"\bnew\s*firmware\s*version\b",
        ],
        "navigation_terms": ["system", "dashboard", "status"],
        "requires_label_value": False,
        "base_weight": 0.65,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "vpn_tunnels": {
        "strong_anchors": [
            "ipsec monitor", "ipsec tunnel", "ipsec tunnels", "vpn tunnels",
            "ssl-vpn tunnel", "get vpn ipsec stats", "vpn tunnel status"
        ],
        "strong_groups": [
            ["vpn", "tunnel"],
            ["vpn", "ipsec"],
            ["ipsec", "phase"],
            ["vpn", "active"],
            ["tunnel", "selectors"],
            ["tunnel", "incoming"],
        ],
        "supporting_anchors": [
            "vpn", "tunnel", "tunnels", "ipsec", "selectors", "phase 1", "phase 2",
            "ike", "active", "inactive", "dialup", "remote gateway", "incoming", "outgoing"
        ],
        "weak_anchors": ["network", "status"],
        "negative_anchors": [],
        "url_anchors": ["/ng/vpn", "vpn/ipsec", "vpn/tunnel"],
        "regex_patterns": [
            r"\bphase\s*[12]\b",
            r"\bipsec\s*tunnels?\b",
            r"\bget\s+vpn\s+ipsec\b",
            r"\b(?:active|inactive)\s+tunnels?\b",
        ],
        "navigation_terms": ["vpn", "dashboard"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.20,
    },

    "routing_table": {
        "strong_anchors": [
            "static route", "routing monitor", "routing table", "active routes",
            "get router info", "get router info routing-table", "fib routes",
            "destination", "gateway ip", "static routes", "is directly connected",
            "directly connected"
        ],
        "strong_groups": [
            ["routing", "gateway"],
            ["routing", "destination"],
            ["static", "route"],
            ["route", "distance"],
            ["route", "metric"],
            ["routing", "monitor"],
            ["routes", "gateway"],
        ],
        "supporting_anchors": [
            "gateway ip", "distance", "metric", "destination", "gateway",
            "next hop", "fib", "static", "direct", "interface"
        ],
        "weak_anchors": ["routing", "network", "routes"],
        "negative_anchors": [
            "/ng/interface", "physical interface", "link status"
        ],
        "url_anchors": ["/ng/routing", "routing/static", "router/", "/routing", "/system/routing"],
        "regex_patterns": [
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}\b",
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}['/]\d{1,2}\b",
            r"\bgateway\s*ip\b",
            r"\bget\s+router\s+info\b",
            r"\b(?:distance|metric)[:\s]+\d+\b",
            r"\bstatic\s+routes?\b",
            r"\b(?:direct|static)\b.*\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            r"\bis\s+directly\s+connected\b",
            r"['/](?:24|32|30|16|8|28|29)\b",
            r"\(port\d*\b",
            r"\b172\.\d+[\+]\d+\b",
            r"\b(?:oyaz|ovz|omz|ouz)\b",
        ],
        "navigation_terms": ["network", "routing", "dashboard"],
        "requires_label_value": False,
        "base_weight": 0.70,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "system_uptime": {
        "strong_anchors": [
            "system uptime", "up time", "system up time", "current uptime", "cluster uptime", "uptime"
        ],
        "strong_groups": [
            ["uptime", "day"],
            ["uptime", "days"],
            ["uptime", "hour"],
            ["uptime", "hours"],
            ["system", "uptime"],
            ["system information", "uptime"],
            ["uptime", "wan ip"],
        ],
        "supporting_anchors": [
            "uptime", "days", "hours", "mins", "system information", "hostname", "current time", "wan ip"
        ],
        "weak_anchors": ["time", "status", "system"],
        "negative_anchors": [
            "virus-db", "ips-db", "bios", "/ng/routing", "/system/dashboard"
        ],
        "url_anchors": [],
        "regex_patterns": [
            r"\b\d+\s*days?,\s*\d+\s*hours?\b",
            r"\b\d+d\s*\d+h(?:\d+m)?\b",
            r"\b\d+[dB]\s*\d+[hm]\s*(?:\d+[ms])?\b",
            r"\buptime[:\s]+\d+\s*(?:day|hour|d|h)",
            r"\bup\s+\d+\s+days\b",
            r"\bcluster\s+uptime\b",
        ],
        "navigation_terms": ["system", "dashboard", "status"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "gui_access": {
        "strong_anchors": [
            "add widget", "+ add widget", "web-based manager", "fortiview summary",
            "dashboard status", "/system/dashboard", "system/dashboard"
        ],
        "strong_groups": [
            ["dashboard", "widget"],
            ["system", "dashboard"],
            ["fortigate", "gui"],
            ["dashboard", "status"],
            ["dashboard", "sessions"],
        ],
        "supporting_anchors": [
            "dashboard", "status", "administrator", "system", "network", "log & report",
            "security profiles", "sessions", "login", "home page", "fortiview"
        ],
        "weak_anchors": ["fortigate", "administrator", "status", "system"],
        "negative_anchors": [
            "cli console", "# get", "get system status"
        ],
        "url_anchors": ["/system/dashboard", "dashboard/1", "dashboard/status", "/ng/dashboard", "dashboard/"],
        "regex_patterns": [
            r"\b\+\s*add\s*widget\b",
            r"\badd\s*widget\b",
            r"\/system\/dashboard\b",
            r"\bdashboard\s*status\b",
        ],
        "navigation_terms": ["dashboard"],
        "requires_label_value": False,
        "base_weight": 0.70,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "cli_access": {
        "strong_anchors": [
            "cli console", "exec ping", "ping statistics", "packets transmitted",
            "get system status", "get system stat", "ssh terminal", "console window", "# get system status",
            "admin@fg", "terminal window", "last reboot reason", "release version information",
            "command parse error", "command fail", "return code"
        ],
        "strong_groups": [
            ["cli", "console"],
            ["ping", "statistics"],
            ["packets", "transmitted"],
            ["get", "system", "status"],
            ["get", "system", "stat"],
            ["bytes", "from"],
            ["packet", "loss"],
        ],
        "supporting_anchors": [
            "terminal", "command", "prompt", "ping", "packets transmitted", "bytes from",
            "packet loss", "rtt min/avg/max", "round-trip", "exec", "admin@"
        ],
        "weak_anchors": ["#", "$", "admin", "console"],
        "negative_anchors": [
            "get system ha status", "ha mode: standalone", "sync status"
        ],
        "url_anchors": [],
        "regex_patterns": [
            r"\b\d+\s*packets\s*transmitted\b",
            r"\b(?:min\/avg\/max|round-trip)\b",
            r"\bexec\s+ping\b",
            r"\bget\s+system\s+stat(?:s|us)?\b",
            r"[A-Za-z0-9_-]+\s*[\*#\$]\s*",
            r"\blast\s+reboot\s+reason\b",
        ],
        "navigation_terms": [],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.25,
    },

    "signature_version": {
        "strong_anchors": [
            "definitions & signatures", "av engine", "ips definitions", "attack definition",
            "antivirus definition", "application control definitions", "database version",
            "distribution network", "update licenses & definitions", "fortiguard definitions",
            "threat database", "ips engine", "application control", "intrusion prevention",
            "botnet", "iot detection", "iot"
        ],
        "strong_groups": [
            ["fortiguard", "updates"],
            ["fortiguard", "definitions"],
            ["signature", "version"],
            ["av", "engine"],
            ["ips", "definitions"],
            ["database", "version"],
            ["attack", "definitions"],
            ["expiration", "date"],
        ],
        "supporting_anchors": [
            "fortiguard", "definitions", "signatures", "signature", "last updated",
            "update licenses", "malicious", "ot threat", "virtual patch", "database",
            "pending", "distribution network"
        ],
        "weak_anchors": ["version", "update", "updates"],
        "negative_anchors": [
            "$ system", "virus-db in cli", "power cycle"
        ],
        "url_anchors": [
            "/ng/system/fortiguard", "/system/fortiguard", "fortiguard updates"
        ],
        "regex_patterns": [
            r"\bdefinitions?\s*&\s*signatures?\b",
            r"\bav\s*engine\b",
            r"\bips\s*definitions?\b",
            r"\blast\s*updated\b",
            r"\bdatabase\s*version\b",
            r"\b\d+\.\d{4,5}\b",
            r"\bexpir(?:atix|ation)\b",
        ],
        "navigation_terms": ["system", "status"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "firewall_datetime": {
        "strong_anchors": [
            "system time", "time zone", "ntp server", "time settings",
            "synchronized with ntp", "manual time settings", "time synchronization"
        ],
        "strong_groups": [
            ["system", "time"],
            ["time", "zone"],
            ["ntp", "synchronized"],
            ["time", "settings"],
            ["clock", "settings"],
            ["ntp", "server"],
        ],
        "supporting_anchors": [
            "ntp", "gmt", "utc", "kuala lumpur", "singapore", "set time",
            "daylight saving", "time synchronization", "clock", "current time",
            "ntp.fortinet.net", "synchronized"
        ],
        "weak_anchors": ["time", "date", "status"],
        "negative_anchors": [
            "config system", "config firewall", "/system/backup", "/system/dashboard"
        ],
        "url_anchors": ["/ng/system/settings", "/system/time", "/system/settings"],
        "regex_patterns": [
            r"\b(?:gmt|utc)\s*[+-]?\d+\b",
            r"\bntp\s*server\b",
            r"\bsynchronized\s*with\b",
            r"\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\b",
            r"\btime\s*zone\b",
            r"\bsystem\s+time[:\s]+\d{4}[-/]\d{2}[-/]\d{2}\b",
        ],
        "navigation_terms": ["system", "settings"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.20,
    },

    "ha_status": {
        "strong_anchors": [
            "high availability", "ha status", "mode: a-p", "active-passive",
            "active-active", "ha mode", "ha group", "get system ha status",
            "get system ha", "standalone mode", "cluster members", "primary unit",
            "secondary unit", "ha cluster", "mode: standalone", "ha mode:", "fgsp",
            "session sync", "haactive-passive", "haactive-active"
        ],
        "strong_groups": [
            ["ha", "status"],
            ["high", "availability"],
            ["cluster", "status"],
            ["ha", "mode"],
            ["get", "system", "ha"],
            ["cluster", "members"],
            ["ha", "standalone"],
        ],
        "supporting_anchors": [
            "cluster", "synchronized", "priority", "sync status", "vcluster",
            "override: disable", "sync:", "primary", "secondary", "hb-device",
            "heartbeat", "mode: standalone", "standalone"
        ],
        "weak_anchors": ["ha", "status"],
        "negative_anchors": [],
        "url_anchors": ["/ng/system/ha", "system/ha", "ha/monitor", "/ha/monitor", "system/ha/monitor", "/ng/system/ha/cluster", "/system/ha/cluster"],
        "regex_patterns": [
            r"\bmode:\s*(?:a-p|a-a|standalone)\b",
            r"\bget\s+system\s+ha(?:\s+status)?\b",
            r"\bcluster\s+(?:status|uptime|members)\b",
            r"\bha\s+cluster\b",
            r"\bhigh\s+availability\b",
            r"\/system\/ha\b",
        ],
        "navigation_terms": ["system", "dashboard"],
        "requires_label_value": False,
        "base_weight": 0.70,
        "supporting_weight": 0.12,
        "negative_penalty": 0.20,
    },

    "system_event": {
        "strong_anchors": [
            "system events", "event log", "event-log", "system event log",
            "event severity", "system activity log", "all events"
        ],
        "strong_groups": [
            ["event", "log"],
            ["system", "events"],
            ["event", "severity"],
            ["log", "severity"],
            ["event", "level"],
            ["event", "message"],
            ["system", "event"],
        ],
        "supporting_anchors": [
            "event", "events", "severity", "critical", "warning", "information",
            "error", "sub type", "log id", "message", "action", "date/time", "user"
        ],
        "weak_anchors": ["log", "logs", "activity"],
        "negative_anchors": [
            "/log/settings", "log settings", "remote log", "fortianalyzer",
            "syslog server", "remote logging", "/system/ha", "/ng/system/ha",
            "high availability", "/ng/system/settings", "/system/settings"
        ],
        "url_anchors": ["/log/event-log", "/log/event", "/ng/log/event"],
        "regex_patterns": [
            r"\bsystem\s+event\s+logs?\b",
            r"\bevent\s+severity\b",
            r"\bseverity:\s*(?:critical|warning|information)\b",
            r"\b(?:critical|warning|information|alert)\b.*\b(?:log\s*id|event)\b",
            r"\bdate\/time\b.*\bseverity\b",
        ],
        "navigation_terms": ["log & report", "system"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.35,
    },

    "log_manager": {
        "strong_anchors": [
            "log settings", "log manager", "remote log", "fortianalyzer",
            "forticloud", "syslog server", "log to fortianalyzer", "log to syslog",
            "logging & analytics", "log forwarding", "disk logging", "remote logging",
            "fortianalyzer/fortimanager", "send logs to", "traffic logs", "traffic log",
            "threat weight", "global settings", "summary logs", "no traffic logs"
        ],
        "strong_groups": [
            ["log", "settings"],
            ["log", "manager"],
            ["remote", "log"],
            ["fortianalyzer", "status"],
            ["syslog", "server"],
            ["logging", "analytics"],
            ["log", "forwarding"],
            ["disk", "logging"],
        ],
        "supporting_anchors": [
            "connected", "upload", "status: real-time", "realtime", "ip address",
            "server", "port 514", "reliable", "traffic logs", "disk usage", "storage",
            "remet log", "traffc log", "traffc logs", "thmat"
        ],
        "weak_anchors": ["log", "logging", "settings"],
        "negative_anchors": [
            "/log/event-log", "/ng/log/event", "event severity", "/system/dashboard"
        ],
        "url_anchors": [
            "/log/settings", "log/config", "settings/logging", "/ng/log/settings"
        ],
        "regex_patterns": [
            r"\/log\/settings\b",
            r"\blog\s*settings\b",
            r"\bfortianalyzer\b",
            r"\bsyslog(?:\s*server)?\b",
            r"\bremote\s*log(?:ging)?\b",
            r"\blogging\s*&\s*analytics\b",
            r"\bsend\s+logs\s+to\b",
            r"\btraffic\s*logs?\b",
            r"\bthreat\s*weight\b",
            r"\bglobal\s*settings\b",
            r"\bno\s+traff[ic]*\s*logs?\b",
            r"\brem[eo]t\s*log\b",
            r"\bth[re]mat\s*w[ec]i[bgh]*t\b",
        ],
        "navigation_terms": ["log & report", "settings"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.25,
    },

    "backup_configuration": {
        "strong_anchors": [
            "backup system configuration", "backup configuration", "backup to local pc",
            "backup to usb", "download backup", "restore system", "backup file",
            "config system", "config firewall", "config router", "config switch",
            "config vpn", "config user", "set hostname", "set uuid", "end\nconfig"
        ],
        "strong_groups": [
            ["backup", "configuration"],
            ["backup", "download"],
            ["backup", ".conf"],
            ["backup", "system"],
            ["backup", "restore"],
        ],
        "supporting_anchors": [
            "backup", "download", ".conf", "restore", "password", "encrypt",
            "revision", "configuration file", "completed", "local pc", "usb disk",
            "config", "set", "end", "next"
        ],
        "weak_anchors": ["configuration", "file", "save", "download"],
        "negative_anchors": [
            "/log/settings", "/ng/system/ha", "/system/ha", "/ng/system/settings",
            "/system/settings", "event logging", "syslog logging", "log settings",
            "remote log", "fortianalyzer", "threat weight", "edit in cli", "additional information"
        ],
        "url_anchors": ["/system/backup", "backup/restore"],
        "regex_patterns": [
            r"\bbackup\s+(?:system\s+)?configuration\b",
            r"\bconfig\s+(?:system|firewall|router|switch|vpn|user|interface)\b",
            r"\bset\s+(?:hostname|uuid|ip|allowaccess|type|mode)\b",
            r"\b(?:backup|download)\b.*\.conf\b",
            r"\bend\s*\n\s*config\b",
        ],
        "navigation_terms": ["system"],
        "requires_label_value": False,
        "base_weight": 0.68,
        "supporting_weight": 0.12,
        "negative_penalty": 0.25,
    },
}
