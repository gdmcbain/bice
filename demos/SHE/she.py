#!/usr/bin/python3
import numpy as np
import matplotlib.pyplot as plt
import shutil
import os
import sys
sys.path.append("../..")  # noqa, needed for relative import of package
from bice import Problem
from bice.time_steppers import RungeKuttaFehlberg45, ImplicitEuler


class SwiftHohenberg(Problem):
    """
    Pseudospectral implementation of the 1-dimensional Swift-Hohenberg Equation
    equation, a nonlinear PDE
    \partial t h &= (r - (kc^2 + \Delta)^2)h + v * h^2 - g * h^3
    """

    def __init__(self, N, L):
        super().__init__()
        # parameters
        self.r = -0.013
        self.kc = 0.5
        self.v = 0.41
        self.g = 1
        # space and fourier space
        self.x = np.linspace(-L/2, L/2, N)
        self.k = np.fft.rfftfreq(N, L / (2. * N * np.pi))
        # initial condition
        self.u = np.cos(2 * np.pi * self.x / 10) * np.exp(-0.005 * self.x**2)
        # initialize time stepper
        self.time_stepper = RungeKuttaFehlberg45(dt=1e-3)
        self.time_stepper.error_tolerance = 1e-7
        self.time_stepper.dt = 1e-3
        # plotting
        self.plotID = 0

    # definition of the equation, using pseudospectral method
    def rhs(self, u):
        u_k = np.fft.rfft(u)
        return np.fft.irfft((self.r - (self.kc**2 - self.k**2)**2) * u_k) + self.v * u**2 - self.g * u**3

    # set higher modes to null, for numerical stability
    def dealias(self, fraction=1./2.):
        u_k = np.fft.rfft(self.u)
        N = len(u_k)
        u_k[-int(N*fraction):] = 0
        self.u = np.fft.irfft(u_k)

    # return the value of the continuation parameter
    def get_continuation_parameter(self):
        return self.r

    # set the value of the continuation parameter
    def set_continuation_parameter(self, v):
        self.r = v

    # plot everything
    def plot(self, fig, ax, sol=None):
        ax[0, 0].plot(self.x, self.u)
        ax[0, 0].set_xlabel("x")
        ax[0, 0].set_ylabel("solution u(x,t)")
        ax[1, 0].plot(self.k, np.abs(np.fft.rfft(self.u)))
        ax[1, 0].set_xlim((0, self.k[-1]/2))
        ax[1, 0].set_xlabel("k")
        ax[1, 0].set_ylabel("fourier spectrum u(k,t)")
        for branch in self.bifurcation_diagram.branches:
            r, norm = branch.data()
            ax[0, 1].plot(r, norm, "--", color="C0")
            r, norm = branch.data(only="stable")
            ax[0, 1].plot(r, norm, color="C0")
            r, norm = branch.data(only="bifurcations")
            ax[0, 1].plot(r, norm, "*", color="C2")
        ax[0, 1].plot(np.nan, np.nan, "*", color="C2", label="bifurcations")
        ax[0, 1].plot(self.r, self.norm(),
                      "x", label="current point", color="black")
        ax[0, 1].set_xlabel("parameter r")
        ax[0, 1].set_ylabel("L2-norm")
        ax[0, 1].legend()
        if sol:
            ev_re = np.real(sol.eigenvalues[:20])
            ev_re_n = np.ma.masked_where(
                ev_re > self.eigval_zero_tolerance, ev_re)
            ev_re_p = np.ma.masked_where(
                ev_re <= self.eigval_zero_tolerance, ev_re)
            ax[1, 1].plot(ev_re_n, "o", color="C0", label="Re < 0")
            ax[1, 1].plot(ev_re_p, "o", color="C1", label="Re > 0")
            ax[1, 1].axhline(0, color="gray")
            ax[1, 1].legend()
            ax[1, 1].set_ylabel("eigenvalues")
        fig.savefig("out/img/{:05d}.svg".format(self.plotID))
        self.plotID += 1
        for a in ax.flatten():
            a.clear()


# create output folder
shutil.rmtree("out", ignore_errors=True)
os.makedirs("out/img", exist_ok=True)

# create problem
problem = SwiftHohenberg(N=512, L=240)

# create figure
fig, ax = plt.subplots(2, 2, figsize=(16, 9))

# time-stepping
n = 0
plotevery = 1000
dudtnorm = 1
if not os.path.exists("initial_state.dat"):
    while dudtnorm > 1e-5:
        # plot
        if n % plotevery == 0:
            problem.plot(fig, ax)
            print("step #: {:}".format(n))
            print("time:   {:}".format(problem.time))
            print("dt:     {:}".format(problem.time_stepper.dt))
            print("|dudt|: {:}".format(dudtnorm))
        n += 1
        # perform timestep
        problem.time_step()
        # perform dealiasing
        problem.dealias()
        # calculate the new norm
        dudtnorm = np.linalg.norm(problem.rhs(problem.u))
        # catch divergent solutions
        if np.max(problem.u) > 1e12:
            break
    # save the state, so we can reload it later
    problem.save("initial_state.dat")
else:
    # load the initial state
    problem.load("initial_state.dat")

# start parameter continuation
problem.continuation_stepper.ds = 1e-2
problem.continuation_stepper.ndesired_newton_steps = 3
problem.continuation_stepper.always_check_eigenvalues = True

n = 0
plotevery = 5
while problem.r > -0.016:
    # perform continuation step
    sol = problem.continuation_step()
    n += 1
    print("step #:", n, " ds:", problem.continuation_stepper.ds)
    # plot
    if n % plotevery == 0:
        problem.plot(fig, ax, sol)

# continuation in reverse direction
# load the initial state
problem.new_branch()
problem.load("initial_state.dat")
problem.r = -0.013
problem.continuation_stepper.ds = -1e-2
while problem.r < -0.002:
    # perform continuation step
    sol = problem.continuation_step()
    n += 1
    print("step #:", n, " ds:", problem.continuation_stepper.ds)
    # plot
    if n % plotevery == 0:
        problem.plot(fig, ax, sol)