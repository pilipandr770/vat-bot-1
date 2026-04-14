"""Country-specific business registry adapters."""

from .de_handelsregister import GermanHandelsregisterAdapter
from .de_bundesanzeiger import BundesanzeigerAdapter
from .epo_patents import EpoPatentsAdapter
from .opencorporates import OpenCorporatesAdapter
from .cz_ares import CzechAresAdapter
from .pl_whitelist import PolishWhiteListAdapter
from .ua_edr import UkrainianEdrAdapter
from .ua_vat import UkrainianVatAdapter
from .ua_sanctions import UkrainianSanctionsAdapter

__all__ = [
    "GermanHandelsregisterAdapter",
    "BundesanzeigerAdapter",
    "EpoPatentsAdapter",
    "OpenCorporatesAdapter",
    "CzechAresAdapter",
    "PolishWhiteListAdapter",
    "UkrainianEdrAdapter",
    "UkrainianVatAdapter",
    "UkrainianSanctionsAdapter",
]
