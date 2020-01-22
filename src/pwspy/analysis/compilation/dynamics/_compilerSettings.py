from dataclasses import dataclass

from pwspy.analysis.compilation.abstract import AbstractCompilerSettings


@dataclass
class DynamicsCompilerSettings(AbstractCompilerSettings):
    """These settings determine how a Dynamics acquisition should be compiled."""
    reflectance: bool
    rms_t: bool
    #TODO what else is there? diffusion?