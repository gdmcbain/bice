#!/usr/bin/python3
import shutil
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
sys.path.append("../..")  # noqa, needed for relative import of package
from acPFC1d import acPFCProblem
from bice import time_steppers
from bice.measure import LyapunovExponentCalculator
from bice import profile, Profiler


# create output folder
shutil.rmtree("out", ignore_errors=True)
os.makedirs("out/img", exist_ok=True)

# create problem
problem = acPFCProblem(N=256, L=16*np.pi)

# create figure
fig = plt.figure(figsize=(16, 9))
ax_exponents = fig.add_subplot(121)
ax_largest = fig.add_subplot(122)
plotID = 0

# time-stepping
n = 0
plotevery = 10
dudtnorm = 1
T = 1000.
if not os.path.exists("initial_state.dat"):
    while problem.time < T:
        # plot
        if n % plotevery == 0:
            problem.plot(ax_exponents)
            fig.savefig("out/img/{:05d}.svg".format(plotID))
            plotID += 1
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
            print("diverged")
            break
    # save the state, so we can reload it later
    problem.save("initial_state.dat")
else:
    # load the initial state
    problem.load("initial_state.dat")

# calculate Lyapunov exponents
problem.time_stepper = time_steppers.BDF2(dt=0.1)
lyapunov = LyapunovExponentCalculator(
    problem, nexponents=20, epsilon=1e-6, nintegration_steps=1)

last10 = []
largest = []

# Profiler.start()

n = 1
plotevery = 10
while True:
    # perform Lyapunov exponent calculation step
    lyapunov.step()
    # store last10 and largest Lyapunov exponents
    last10 = [lyapunov.exponents] + last10[:9]
    largest += [np.max(lyapunov.exponents)]
    print("Lyapunov exponents:", lyapunov.exponents)
    n += 1
    # plot
    if n % plotevery == 0:
        # clear axes
        ax_largest.clear()
        ax_exponents.clear()
        if lyapunov.nexponents > 1:
            # plot spectrum
            for ccount, exponents in enumerate(last10):
                ax_exponents.plot(exponents, marker='.', color='{:.1f}'.format(
                    ccount/len(last10)), ls='')
            ax_exponents.plot(lyapunov.exponents, marker="o")
        else:
            # plot solution
            problem.plot(ax_exponents)
        # plot largest exponent
        ax_largest.plot(largest)
        fig.savefig("out/img/{:05d}.svg".format(plotID))
        plotID += 1
        # show performance analysis
        # Profiler.print_summary()
