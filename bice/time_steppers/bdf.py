import numpy as np
import scipy.integrate
from .time_steppers import TimeStepper


class BDF2(TimeStepper):
    """
    'Backward Differentiation Formula' scheme of order 2
    """

    def __init__(self, dt=1e-3):
        super().__init__(dt)
        self.order = 2

    def step(self, problem):
        # advance in time
        problem.time += self.dt

        # recover the history (impulsive start, if history is missing)
        u_1 = problem.u
        u_2 = problem.history.u(1) if problem.history.length > 1 else u_1
        # obtain the problem's mass matrix
        M = problem.mass_matrix()

        def f(u):
            # assemble the system
            return self.dt * problem.rhs(u) - M.dot(3*u - 4*u_1 + u_2)

        def J(u):
            # Jacobian of the system
            return self.dt * problem.jacobian(u) - 3*M
        # solve it with a Newton solver
        problem.u = problem.newton_solver.solve(f, problem.u, J)


class BDF(TimeStepper):
    """
    'Backward Differentiation Formula' scheme of variable order
    using scipy.integrate
    """

    def __init__(self, problem, dt_max=
    np.inf):
        super().__init__()
        self.problem = problem
        self.rtol = 1e-5
        self.atol = 1e-8
        self.dt_max = dt_max
        self.factory_reset()

    def step(self, problem):
        # perform the step
        self.bdf.step()
        # assign the new variables
        self.dt = self.bdf.step_size
        self.problem.time = self.bdf.t
        self.problem.u = self.bdf.y

    def factory_reset(self):
        # create wrapper for the right-hand side
        def f(t, u):
            self.problem.time = t
            return self.problem.rhs(u)
        # create instance of scipy.integrate.BDF
        self.bdf = scipy.integrate.BDF(
            f, self.problem.time, self.problem.u, self.problem.time+1e18, max_step=self.dt_max, rtol=self.rtol, atol=self.atol, vectorized=False)
