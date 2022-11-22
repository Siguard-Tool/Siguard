# We use RsT document formatting in docstring. For example :param to mark parameters.
# See PEP 287
__docformat__ = "restructuredtext"
import logging

# Accept siguard.VERSION to get mythril's current version number
from .__version__ import __version__ as VERSION  # NOQA
from siguard.plugin.loader import MythrilPluginLoader

log = logging.getLogger(__name__)
