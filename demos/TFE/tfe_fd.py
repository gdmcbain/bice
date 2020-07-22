#!/usr/bin/python3
import sys
sys.path.append("../..")  # noqa, needed for relative import of package
import os
import shutil
import matplotlib.pyplot as plt
import numpy as np
from bice.time_steppers import RungeKuttaFehlberg45, ImplicitEuler, RungeKutta4
from bice import Problem


class ThinFilm(Problem):
    """
    Finite difference implementation of the 1-dimensional Swift-Hohenberg Equation
    equation, a nonlinear PDE
    \partial t h &= (r - (kc^2 + \Delta)^2)h + v * h^2 - g * h^3
    """

    def __init__(self, N, L):
        super().__init__()
        # parameters

        # impose a translation constraint?
        self.translation_constraint = False
        # space and fourier space
        self.x = np.linspace(-L/2, L/2, N, endpoint=False)
        self.dx = self.x[1] - self.x[0]
        self.k = np.fft.rfftfreq(N, L / (2. * N * np.pi))
        # initial condition
        self.u = np.ones(N) * 3
        self.u = 2 * np.cos(self.x*2*np.pi/L) + 3
        # self.u = np.maximum(10 * np.cos(self.x / 5), 1)
        # initialize time stepper
        self.time_stepper = RungeKutta4()
        # self.time_stepper = RungeKuttaFehlberg45()
        self.time_stepper.error_tolerance = 1e-1
        self.time_stepper.dt = 4e-5
        # plotting
        self.plotID = 0
        # volume
        self.fixed_volume = 0
        # FD matrices
        self.nabla = None
        self.laplace = None
        self.build_matrices()

    def build_matrices(self):
        N = self.dim
        I = np.eye(N)
        self.nabla = np.zeros((N, N))
        self.nabla += -3*np.roll(I, -4, axis=1)
        self.nabla += 32*np.roll(I, -3, axis=1)
        self.nabla += -168*np.roll(I, -2, axis=1)
        self.nabla += 672*np.roll(I, -1, axis=1)
        self.nabla -= 672*np.roll(I, 1, axis=1)
        self.nabla -= -168*np.roll(I, 2, axis=1)
        self.nabla -= 32*np.roll(I, 3, axis=1)
        self.nabla -= -3*np.roll(I, 4, axis=1)
        self.nabla /= self.dx * 840

        self.laplace = np.zeros((N, N))
        self.laplace += -9*np.roll(I, -4, axis=1)
        self.laplace += 128*np.roll(I, -3, axis=1)
        self.laplace += -1008*np.roll(I, -2, axis=1)
        self.laplace += 8064*np.roll(I, -1, axis=1)
        self.laplace += -14350*np.roll(I, 0, axis=1)
        self.laplace += 8064*np.roll(I, 1, axis=1)
        self.laplace += -1008*np.roll(I, 2, axis=1)
        self.laplace += 128*np.roll(I, 3, axis=1)
        self.laplace += -9*np.roll(I, 4, axis=1)
        self.laplace /= self.dx**2 * 5040

    # definition of the equation, using pseudospectral method

    def rhs(self, u):
        if self.translation_constraint:
            vel = u[-1]
            h = u[:-1]
        else:
            vel = 0
            h = u

        # definition of the TFE
        # dh/dt = d/dx (h^3 d/dx ( - d^2/dx^2 h - Pi(h) ))

        res = np.zeros(self.dim)
        dFdh = -np.matmul(self.laplace, h) - self.djp(h)
        res[:h.size] = np.matmul(
            self.nabla, h**3 * np.matmul(self.nabla, dFdh))

        # definition of the constraint
        if self.translation_constraint:
            h_old = self.u[:-1]
            # this is the classical constraint: du/dx * du/dp = 0
            # res[u.size] = np.dot(
            #     np.fft.irfft(-1j*self.k*np.fft.rfft(u_old)), u-u_old)
            # this is the alternative center-of-mass constraint, requires less Fourier transforms :-)
            res[u.size] = np.dot(self.x, h-h_old)
        return res

    # The mass matrix determines the linear relation of the rhs to the temporal derivatives dudt
    def mass_matrix(self):
        mm = np.eye(self.dim)
        # if constraint is enabled, the constraint equation has no time evolution
        if self.translation_constraint:
            mm[-1, -1] = 0
        return mm

    # disjoining pressure and derivatives
    def djp(self, h):
        return 1./h**6 - 1./h**3

    def ddjp_dh(self, h):
        return -6./h**7 + 3./h**4

    def d2djp_dh2(self, h):
        return 42./h**8 - 12./h**5

    # return the value of the continuation parameter
    def get_continuation_parameter(self):
        return self.fixed_volume

    # set the value of the continuation parameter
    def set_continuation_parameter(self, v):
        self.fixed_volume = v

    # plot everything
    def plot(self, fig, ax, sol=None):
        h = self.u
        if self.translation_constraint:
            h = h[:-1]
        ax[0, 0].plot(self.x, h)
        ax[0, 0].set_xlabel("x")
        ax[0, 0].set_ylabel("solution h(x,t)")
        ax[0, 0].set_ylim((0, np.max(h)*1.1))
        if sol and len(sol.eigenvectors) > 0:
            ax[1, 0].plot(np.real(sol.eigenvectors[0]))
            ax[1, 0].set_ylabel("eigenvector")
        else:
            ax[1, 0].plot(self.k, np.abs(np.fft.rfft(h)))
            ax[1, 0].set_xlim((0, self.k[-1]))
            ax[1, 0].set_xlabel("k")
            ax[1, 0].set_ylabel("fourier spectrum h(k,t)")
            ax[1, 0].set_yscale("log")
        for branch in self.bifurcation_diagram.branches:
            r, norm = branch.data()
            ax[0, 1].plot(r, norm, "--", color="C0")
            r, norm = branch.data(only="stable")
            ax[0, 1].plot(r, norm, color="C0")
            r, norm = branch.data(only="bifurcations")
            ax[0, 1].plot(r, norm, "*", color="C2")
        ax[0, 1].plot(np.nan, np.nan, "*", color="C2", label="bifurcations")
        ax[0, 1].plot(self.fixed_volume, self.norm(),
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
        else:
            ax[1, 1].plot(problem.x, problem.rhs(problem.u), label="dh/dt")
            ax[1, 1].set_xlabel("x")
            ax[1, 1].set_ylabel("dh/dt")
        fig.savefig("out/img/{:05d}.svg".format(self.plotID))
        self.plotID += 1
        for a in ax.flatten():
            a.clear()


# create output folder
shutil.rmtree("out", ignore_errors=True)
os.makedirs("out/img", exist_ok=True)

# create problem
problem = ThinFilm(N=256, L=100)

problem.build_matrices()

# create figure
fig, ax = plt.subplots(2, 2, figsize=(16, 9))

# time-stepping
n = 0
plotevery = 1000
dudtnorm = 1
if not os.path.exists("initial_state2.dat"):
    while dudtnorm > 1e-8:
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
        # calculate the new norm
        dudtnorm = np.linalg.norm(problem.rhs(problem.u))
        # catch divergent solutions
        if np.max(problem.u) > 1e12:
            print("Aborted.")
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

problem.translation_constraint = True
problem.u = np.append(problem.u, [0])

# n = 0
# plotevery = 5
# while problem.r > -0.016:
#     # perform continuation step
#     sol = problem.continuation_step()
#     n += 1
#     print("step #:", n, " ds:", problem.continuation_stepper.ds)
#     # plot
#     if n % plotevery == 0:
#         problem.plot(fig, ax, sol)

# # continuation in reverse direction
# # load the initial state
# problem.new_branch()
# problem.load("initial_state.dat")
# problem.r = -0.013
# problem.continuation_stepper.ds = -1e-2
# while problem.r < -0.002:
#     # perform continuation step
#     sol = problem.continuation_step()
#     n += 1
#     print("step #:", n, " ds:", problem.continuation_stepper.ds)
#     # plot
#     if n % plotevery == 0:
#         problem.plot(fig, ax, sol)