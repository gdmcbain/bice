#!/usr/bin/python3
import numpy as np
import matplotlib.pyplot as plt
import shutil
import os
import sys
sys.path.append("../..")  # noqa, needed for relative import of package
from bice import Problem, Equation
from bice.time_steppers import RungeKuttaFehlberg45, RungeKutta4, BDF2, BDF
from bice.constraints import *
from bice.solvers import *
from bice.fem import FiniteElementEquation, OneDimMesh


class ThinFilmEquation(FiniteElementEquation):
    r"""
     Finite element implementation of the 1-dimensional Thin-Film Equation
     equation
     dh/dt = d/dx (h^3 d/dx ( - d^2/dx^2 h - Pi(h) ))
     with the disjoining pressure:
     Pi(h) = 1/h^3 - 1/h^6
     """

    def __init__(self, N, L):
        super().__init__()
        # parameters: none
        # setup the mesh
        self.L = L
        self.mesh = OneDimMesh(N, L, -L/2)
        # initial condition
        h0 = 5
        a = 3/20. / (h0-1)
        self.u = np.maximum(-a*self.x[0]*self.x[0] + h0, 1)
        # build finite element matrices
        self.build_FEM_matrices()

    # definition of the equation, using finite element method
    def rhs(self, h):
        return -np.matmul(self.laplace, h) - np.matmul(self.M, self.djp(h))

    # disjoining pressure
    def djp(self, h):
        return 1./h**6 - 1./h**3

    # no dealiasing for the FD version
    def dealias(self, u, real_space=False, ratio=1./2.):
        return u

    def first_spatial_derivative(self, u, direction=0):
        return np.matmul(self.nabla[direction], u)

    def plot(self, ax):
        ax.set_xlabel("x")
        ax.set_ylabel("solution h(x,t)")
        ax.plot(self.x[0], self.u, marker="x")

        # estimate error
        dx = np.diff(problem.tfe.x[0])
        error_estimate = problem.tfe.laplace.dot(problem.tfe.u)[:-1] * dx

        ax.plot((self.x[0][:-1] + self.x[0][1:])/2, error_estimate)


class ThinFilm(Problem):

    def __init__(self, N, L):
        super().__init__()
        # Add the Thin-Film equation to the problem
        self.tfe = ThinFilmEquation(N, L)
        self.add_equation(self.tfe)
        # Generate the volume constraint
        self.volume_constraint = VolumeConstraint(self.tfe)
        self.volume_constraint.fixed_volume = 0
        # Generate the translation constraint
        self.translation_constraint = TranslationConstraint(self.tfe)
        # initialize time stepper
        # self.time_stepper = RungeKutta4()
        # self.time_stepper = RungeKuttaFehlberg45()
        # self.time_stepper.error_tolerance = 1e1
        # self.time_stepper.dt = 3e-5
        self.time_stepper = BDF(self)  # better for FD
        # assign the continuation parameter
        self.continuation_parameter = (self.volume_constraint, "fixed_volume")

    # set higher modes to null, for numerical stability
    def dealias(self, fraction=1./2.):
        self.tfe.u = self.tfe.dealias(self.tfe.u, True)

    def norm(self):
        return np.trapz(self.tfe.u, self.tfe.x[0])


# create output folder
shutil.rmtree("out", ignore_errors=True)
os.makedirs("out/img", exist_ok=True)

# create problem
problem = ThinFilm(N=120, L=99)

# Impose the constraints
problem.volume_constraint.fixed_volume = np.trapz(
    problem.tfe.u, problem.tfe.x[0])
problem.add_equation(problem.volume_constraint)
problem.add_equation(problem.translation_constraint)

# problem.newton_solver = MyNewtonSolver()
# problem.newton_solver.convergence_tolerance = 1e-6

# create figure
fig, ax = plt.subplots(1, 1, figsize=(16, 9))
plotID = 0

# plot
problem.tfe.plot(ax)
fig.savefig("out/img/{:05d}.png".format(plotID))
ax.clear()
plotID += 1

# newton solve
# problem.newton_solve()

# plot
problem.tfe.plot(ax)
fig.savefig("out/img/{:05d}.png".format(plotID))
ax.clear()
plotID += 1


for i in range(30):
    print("solving")
    problem.newton_solve()
    print("adapting")
    # adapt mesh
    problem.tfe.adapt()

    # plot
    problem.tfe.plot(ax)
    fig.savefig("out/img/{:05d}.png".format(plotID))
    ax.clear()
    plotID += 1