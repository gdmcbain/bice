"""
The 'core' package contains all of bice's basic functionality.
"""

from .problem import Problem
from .equation import Equation, EquationGroup
from .solution import Solution, Branch, BifurcationDiagram
from .solvers import MyNewtonSolver, NewtonKrylovSolver, EigenSolver
from .profiling import profile, Profiler

__all__ = [
    'Problem',
    'Equation', 'EquationGroup',
    'Solution', 'Branch', 'BifurcationDiagram',
    'MyNewtonSolver', 'NewtonKrylovSolver', 'EigenSolver',
    'profile', 'Profiler'
]
