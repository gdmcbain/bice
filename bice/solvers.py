import numpy as np
import scipy.optimize
import scipy.sparse
import scipy.linalg


class NewtonSolver:
    # TODO: catch errors, get number of iterations...
    def __init__(self):
        self.method = "krylov"

    def solve(self, f, u):
        # TODO: find an optimal solver
        return scipy.optimize.newton_krylov(f, u)
        # return scipy.optimize.newton(f, u)
        # return scipy.optimize.root(f, u, method=self.method)


class EigenSolver:

    def solve(self, A, M=None, k=None, sigma=1):
        if k is None:
            # if no number of values was specified, use a direct eigensolver for computing all eigenvalues
            eigenvalues, eigenvectors = scipy.linalg.eig(A, M)
        else:
            # else: compute only the largest k eigenvalues with an iterative eigensolver
            # this iterative eigensolver relies on ARPACK (Arnoldi method)
            # A: matrix of which we compute the eigenvalues
            # k: number of eigenvalues to compute in iterative method
            # M: mass matrix for generized eigenproblem A*x=w*M*x
            # which: order of eigenvalues to compute ('LM' = largest magnitude is default and the fastest)
            # sigma: Find eigenvalues near sigma using shift-invert mode.
            # v0: Starting vector for iteration. Default: random.
            #     This may not be deterministic, since it is random! For this reason, pde2path uses a [1,...,1]-vector
            # For more info, see the documentation:
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigs.html
            eigenvalues, eigenvectors = scipy.sparse.linalg.eigs(
                A, k=k, M=M, sigma=sigma, which='LM')
        # sort by largest eigenvalue (largest real part) and filter infinite eigenvalues
        idx = np.argsort(eigenvalues)[::-1]
        idx = idx[np.isfinite(eigenvalues[idx])]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors.T[idx]
        return (eigenvalues, eigenvectors)
