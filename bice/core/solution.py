"""
This file describes a data structure for Solutions, Branches and BifurcationDiagrams of a Problem.
"""
import numpy as np


class Solution:
    """
    Stores the solution of a problem, including the relevant parameters,
    and some information on the solution.
    """

    # static variable counting the total number of Solutions
    solution_count = 0

    def __init__(self, problem=None):
        # generate solution ID
        Solution.solution_count += 1
        # unique identifier of the solution
        self.id = Solution.solution_count
        # the current problem state as a dictionary of data (equation's unknowns and parameters)
        # TODO: storing each solution's data may eat up some memory
        #       do we need to save every solution? maybe save bifurcations only
        # save the current data of the problem, so we can restore the point
        self.data = problem.save() if problem is not None else {}
        # value of the continuation parameter
        self.p = problem.get_continuation_parameter() if problem is not None else 0
        # value of the solution norm
        self.norm = problem.norm() if problem is not None else 0
        # number of true positive eigenvalues
        self.nunstable_eigenvalues = None
        # number of true positive and imaginary eigenvalues
        self.nunstable_imaginary_eigenvalues = None
        # optional reference to the corresponding branch
        self.branch = None
        # cache for the bifurcation type
        self._bifurcation_type = None

    # how many eigenvalues have crossed the imaginary axis with this solution?
    @property
    def neigenvalues_crossed(self):
        # if we do not know the number of unstable eigenvalues, we have no result
        if self.nunstable_eigenvalues is None:
            return None
        # else, compare with the nearest previous neighbor that has info on eigenvalues
        # get branch points with eigenvalue info
        bps = [s for s in self.branch.solutions if s.nunstable_eigenvalues is not None]
        # find index of previous solution
        index = bps.index(self) - 1
        if index < 0:
            # if there is no previous solution with info on eigenvalues, we have no result
            return None
        # return the difference in unstable eigenvalues to the previous solution
        return self.nunstable_eigenvalues - bps[index].nunstable_eigenvalues

    # how many eigenvalues have crossed the imaginary axis with this solution?
    @property
    def nimaginary_eigenvalues_crossed(self):
        # if we do not know the number of unstable eigenvalues, we have no result
        if self.nunstable_imaginary_eigenvalues is None:
            return None
        # else, compare with the nearest previous neighbor that has info on eigenvalues
        # get branch points with eigenvalue info
        bps = [
            s for s in self.branch.solutions if s.nunstable_imaginary_eigenvalues is not None]
        # find index of previous solution
        index = bps.index(self) - 1
        if index < 0:
            # if there is no previous solution with info on eigenvalues, we have no result
            return None
        # return the difference in unstable eigenvalues to the previous solution
        return self.nunstable_imaginary_eigenvalues - bps[index].nunstable_imaginary_eigenvalues

    # is the solution stable?
    def is_stable(self):
        # if we don't know the number of eigenvalues, return None
        if self.nunstable_eigenvalues is None:
            return None
        # if there is any true positive eigenvalues, the solution is not stable
        if self.nunstable_eigenvalues > 0:
            return False
        # otherwise, the solution is considered to be stable (or metastable at least)
        return True

    # is the solution point a bifurcation?
    def is_bifurcation(self):
        # get bifurcation type (possibly from cache)
        bif_type = self.bifurcation_type()
        # if it is not a regular point, return True
        return bif_type not in [None, ""]

    # what type of bifurcation is the solution
    # TODO: rename to "type" ? bifurcation.bifurcation_type() looks weird...
    def bifurcation_type(self, update=False):
        # check if bifurcation type is cached
        if self._bifurcation_type is not None and not update:
            return self._bifurcation_type
        # check for number of eigenvalues that crossed zero
        nev_crossed = self.neigenvalues_crossed
        # if unknown or no eigenvalues crossed zero, the point is no bifurcation
        if nev_crossed in [None, 0]:
            self._bifurcation_type = ""
            return self._bifurcation_type
        # otherwise it is some kind of bifurcation point (BP)
        # self._bifurcation_type = "BP"
        # use +/- signs corresponding to their null-eigenvalues as type for regular bifurcations
        n = nev_crossed
        self._bifurcation_type = "+"*n if n > 0 else "-"*(-n)
        # check for Hopf bifurcations by number of imaginary eigenvalues that crossed zero
        nev_imag_crossed = self.nimaginary_eigenvalues_crossed
        # if it is not unknown or zero or one, this must be a Hopf point
        if nev_imag_crossed not in [None, 0, 1]:
            self._bifurcation_type = "HP"
        # return type
        return self._bifurcation_type

    # get access to the previous solution in the branch
    def get_neighboring_solution(self, distance):
        # if we don't know the branch, there is no neighboring solutions
        if self.branch is None:
            return None
        index = self.branch.solutions.index(self) + distance
        # if index out of range, there is no neighbor at requested distance
        if index < 0 or index >= len(self.branch.solutions):
            return None
        # else, return the neighbor
        return self.branch.solutions[index]


class Branch:
    """
    A branch is obtained from a parameter continuation and stores a list of solution objects,
    the corresponding value of the continuation parameter(s) and the norm.
    """

    # static variable counting the number of Branch instances
    branch_count = 0

    def __init__(self):
        # generate branch ID
        Branch.branch_count += 1
        # unique identifier of the branch
        self.id = Branch.branch_count
        # list of solutions along the branch
        self.solutions = []

    # is the current branch empty?
    def is_empty(self):
        return len(self.solutions) == 0

    # add a solution to the branch
    def add_solution_point(self, solution):
        # assign this branch as the solution's branch
        solution.branch = self
        # add solution to list
        self.solutions.append(solution)

    # remove a solution from the branch
    def remove_solution_point(self, solution):
        self.solutions.remove(solution)

    # list of continuation parameter values along the branch
    def parameter_vals(self):
        return [s.p for s in self.solutions]

    # list of solution norm values along the branch
    def norm_vals(self):
        return [s.norm for s in self.solutions]

    # list all bifurcation points on the branch
    def bifurcations(self):
        return [s for s in self.solutions if s.is_bifurcation()]

    # returns the list of parameters and norms of the branch
    # optional argument only (str) may restrict the data to:
    #    - only="stable": stable parts only
    #    - only="unstable": unstable parts only
    #    - only="bifurcations": bifurcations only
    def data(self, only=None):
        if only is None:
            condition = False
        elif only == "stable":
            condition = [not s.is_stable() for s in self.solutions]
        elif only == "unstable":
            condition = [s.is_stable() for s in self.solutions]
        elif only == "bifurcations":
            condition = [not s.is_bifurcation() for s in self.solutions]
        # mask lists where condition is met and return
        pvals = np.ma.masked_where(condition, self.parameter_vals())
        nvals = np.ma.masked_where(condition, self.norm_vals())
        return (pvals, nvals)

    # store the branch to the disk in a format that allows for restoring it later
    def save(self, filename):
        # dict of data to store
        data = {}
        data["solution_data"] = [s.data for s in self.solutions]
        data["norm"] = [s.norm for s in self.solutions]
        data["p"] = [s.p for s in self.solutions]
        data["nunstable_eigenvalues"] = [
            s.nunstable_eigenvalues for s in self.solutions]
        data["nunstable_imaginary_eigenvalues"] = [
            s.nunstable_imaginary_eigenvalues for s in self.solutions]
        # save everything to the file
        np.savez(filename, **data)


class BifurcationDiagram:
    """
    Basically just a list of branches and methods to act upon.
    Also: a fancy plotting method.
    """

    def __init__(self):
        # list of branches
        self.branches = []
        # storage for the currently active branch
        self.active_branch = self.new_branch()
        # x-limits of the diagram
        self.xlim = None
        # y-limits of the diagram
        self.ylim = None
        # name of the continuation parameter
        self.parameter_name = None
        # name of the norm
        self.norm_name = "norm"

    # create a new branch
    def new_branch(self, active=True):
        branch = Branch()
        self.branches.append(branch)
        if active:
            self.active_branch = branch
        return branch

    # return the latest solution in the diagram
    def current_solution(self):
        return self.active_branch.solutions[-1]

    # return a branch by its ID
    def get_branch_by_ID(self, branch_id):
        for branch in self.branches:
            if branch.id == branch_id:
                return branch
        return None

    # remove a branch from the BifurcationDiagram by its ID
    def remove_branch_by_ID(self, branch_id):
        self.branches = [b for b in self.branches if b.id != branch_id]

    # plot the bifurcation diagram
    def plot(self, ax):
        if self.xlim is not None:
            ax.set_xlim(self.xlim)
        if self.ylim is not None:
            ax.set_ylim(self.ylim)
        # plot every branch separately
        for branch in self.branches:
            p, norm = branch.data()
            # ax.plot(p, norm, "o", color="C0")
            ax.plot(p, norm, linewidth=0.7, color="C0")
            p, norm = branch.data(only="stable")
            ax.plot(p, norm, linewidth=1.8, color="C0")
            p, norm = branch.data(only="bifurcations")
            ax.plot(p, norm, "*", color="C2")
            # annotate bifurcations with their types
            for bif in branch.bifurcations():
                s = bif.bifurcation_type()
                ax.annotate(" "+s, (bif.p, bif.norm))
        ax.plot(np.nan, np.nan, "*", color="C2", label="bifurcations")
        ax.set_xlabel(self.parameter_name)
        ax.set_ylabel(self.norm_name)
        ax.legend()

    # load a branch from a file into the diagram, that was stored with Branch.save(filename)
    def load_branch(self, filename):
        # create a new branch
        branch = self.new_branch(active=False)
        # load data dictionary from the file
        data = np.load(filename, allow_pickle=True)
        # restore the solutions and their data
        for i in range(len(data["norm"])):
            sol = Solution()
            sol.data = data["solution_data"][i]
            sol.norm = data["norm"][i]
            sol.p = data["p"][i]
            sol.nunstable_eigenvalues = data["nunstable_eigenvalues"][i]
            sol.nunstable_imaginary_eigenvalues = data["nunstable_imaginary_eigenvalues"][i]
            branch.add_solution_point(sol)
