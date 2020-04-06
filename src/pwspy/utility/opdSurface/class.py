
import numpy as np
import pandas as pd
from scipy import sparse, ndimage as ndi
from scipy.sparse import csgraph
from .nputil import pad, raveled_steps_to_neighbors

def edge(graph, row, col): #Length of edge
    start, end = graph.indptr[row], graph.indptr[row + 1]
    for i in range(start, end):
        if graph.indices[i] == col:
            return graph.data[i]
    return 0.

def neighbors(graph, row):
    loc, stop = graph.indptr[row], graph.indptr[row + 1]
    return graph.indices[loc:stop]


def _pixel_graph(image, steps, distances, num_edges):
    row = np.empty(num_edges, dtype=int)
    col = np.empty(num_edges, dtype=int)
    data = np.empty(num_edges, dtype=float)
    image = image.ravel()
    n_neighbors = steps.size
    start_idx = np.max(steps)
    end_idx = image.size + np.min(steps)
    k = 0
    for i in range(start_idx, end_idx + 1):
        if image[i] != 0:
            for j in range(n_neighbors):
                n = steps[j] + i
                if image[n] != 0 and image[n] != image[i]:
                    row[k] = image[i]
                    col[k] = image[n]
                    data[k] = distances[j]
                    k += 1
    graph = sparse.coo_matrix((data[:k], (row[:k], col[:k]))).tocsr()
    return graph


def _build_paths(jgraph, indptr, indices, path_data, visited, degrees):
    indptr_i = 0
    indices_j = 0
    # first, process all nodes in a path to an endpoint or junction
    for node in range(1, jgraph.shape[0]):
        if degrees[node] > 2 or degrees[node] == 1 and not visited[node]:
            for neighbor in neighbors(jgraph, node):
                if not visited[neighbor]:
                    n_steps = _walk_path(jgraph, node, neighbor, visited,
                                         degrees, indices, path_data,
                                         indices_j)
                    visited[node] = True
                    indptr[indptr_i + 1] = indptr[indptr_i] + n_steps
                    indptr_i += 1
                    indices_j += n_steps
    # everything else is by definition in isolated cycles
    for node in range(1, jgraph.shape[0]):
        if degrees[node] > 0:
            if not visited[node]:
                visited[node] = True
                neighbor = jgraph.neighbors(node)[0]
                n_steps = _walk_path(jgraph, node, neighbor, visited, degrees,
                                     indices, path_data, indices_j)
                indptr[indptr_i + 1] = indptr[indptr_i] + n_steps
                indptr_i += 1
                indices_j += n_steps
    return indptr_i + 1, indices_j


def _walk_path(jgraph, node, neighbor, visited, degrees, indices, path_data, startj):
    indices[startj] = node
    path_data[startj] = jgraph.node_properties[node]
    j = startj + 1
    while degrees[neighbor] == 2 and not visited[neighbor]:
        indices[j] = neighbor
        path_data[j] = jgraph.node_properties[neighbor]
        n1, n2 = jgraph.neighbors(neighbor)
        nextneighbor = n1 if n1 != node else n2
        node, neighbor = neighbor, nextneighbor
        visited[node] = True
        j += 1
    indices[j] = neighbor
    path_data[j] = jgraph.node_properties[neighbor]
    visited[neighbor] = True
    return j - startj + 1


def _build_skeleton_path_graph(graph):
    max_num_cycles = graph.indices.size // 4
    _buffer_size_offset = max_num_cycles
    degrees = np.diff(graph.indptr)
    visited = np.zeros(degrees.shape, dtype=bool)
    endpoints = (degrees != 2)
    endpoint_degrees = degrees[endpoints]
    num_paths = np.sum(endpoint_degrees)
    path_indptr = np.zeros(num_paths + _buffer_size_offset, dtype=int)
    n_points = (graph.indices.size + np.sum(endpoint_degrees - 1) +
                max_num_cycles)
    path_indices = np.zeros(n_points, dtype=int)
    path_data = np.zeros(path_indices.shape, dtype=float)
    m, n = _build_paths(graph, path_indptr, path_indices, path_data,
                        visited, degrees)
    paths = sparse.csr_matrix((path_data[:n], path_indices[:n],
                               path_indptr[:m]), shape=(m - 1, n))
    return paths


class Skeleton:
    def __init__(self, skeleton_image):
        self.degrees_image = _generateDegreesImage(skeleton_image)
        self.graph, self.coordinates = skeleton_to_csgraph(skeleton_image, self.degrees_image)
        self.paths = _build_skeleton_path_graph(self.graph)
        self.n_paths = self.paths.shape[0]
        self._distances = None
        self.degrees = np.diff(self.graph.indptr)
        self.skeleton_image = skeleton_image

    def path(self, index):
        start, stop = self.paths.indptr[index:index + 2]
        return self.paths.indices[start:stop]

    def path_coordinates(self, index):
        """Return the image coordinates of the pixels in the path.
        Parameters
        ----------
        index : int
            The desired path.
        Returns
        -------
        path_coords : array of float
            The (image) coordinates of points on the path, including endpoints.
        """
        path_indices = self.path(index)
        return self.coordinates[path_indices]

    def path_lengths(self):
        """Return the length of each path on the skeleton.
        Returns
        -------
        lengths : array of float
            The length of all the paths in the skeleton.
        """
        if self._distances is None:
            self._distances = np.empty(self.n_paths, dtype=float)
            for i in range(len(self._distances)):
                path = self.path(i)
                d = 0.
                n = len(path)
                for i in range(n - 1):
                    u, v = path[i], path[i + 1]
                    d += edge(self.graph, u, v)
                self._distances[i] = d
        return self._distances


def summarize(skel: Skeleton):
    """Compute statistics for every skeleton and branch in ``skel``.
    Parameters
    ----------
    skel : skan.csr.Skeleton
        A Skeleton object.
    Returns
    -------
    summary : pandas.DataFrame
        A summary of the branches including branch length, mean branch value,
        branch euclidean distance, etc.
    """
    summary = {}
    ndim = skel.coordinates.shape[1]
    _, skeleton_ids = csgraph.connected_components(skel.graph,
                                                   directed=False)
    endpoints_src = skel.paths.indices[skel.paths.indptr[:-1]]
    endpoints_dst = skel.paths.indices[skel.paths.indptr[1:] - 1]
    summary['skeleton-id'] = skeleton_ids[endpoints_src]
    summary['node-id-src'] = endpoints_src
    summary['node-id-dst'] = endpoints_dst
    summary['branch-distance'] = skel.path_lengths()
    deg_src = skel.degrees[endpoints_src]
    deg_dst = skel.degrees[endpoints_dst]
    kind = np.full(deg_src.shape, 2)  # default: junction-to-junction
    kind[(deg_src == 1) | (deg_dst == 1)] = 1  # tip-junction
    kind[(deg_src == 1) & (deg_dst == 1)] = 0  # tip-tip
    kind[endpoints_src == endpoints_dst] = 3  # cycle
    summary['branch-type'] = kind
    summary['mean-pixel-value'] = skel.path_means()
    summary['stdev-pixel-value'] = skel.path_stdev()
    for i in range(ndim):  # keep loops separate for best insertion order
        summary[f'image-coord-src-{i}'] = skel.coordinates[endpoints_src, i]
    for i in range(ndim):
        summary[f'image-coord-dst-{i}'] = skel.coordinates[endpoints_dst, i]
    coords_real_src = skel.coordinates[endpoints_src]
    for i in range(ndim):
        summary[f'coord-src-{i}'] = coords_real_src[:, i]
    coords_real_dst = skel.coordinates[endpoints_dst]
    for i in range(ndim):
        summary[f'coord-dst-{i}'] = coords_real_dst[:, i]
    summary['euclidean-distance'] = (
        np.sqrt((coords_real_dst - coords_real_src) ** 2 @ np.ones(ndim))
    )
    df = pd.DataFrame(summary)
    return df


def _uniquify_junctions(csmat, pixel_indices, junction_labels, junction_centroids):
    """Replace clustered pixels with degree > 2 by a single "floating" pixel.
    Parameters
    ----------
    csmat : NBGraph
        The input graph.
    pixel_indices : array of int
        The raveled index in the image of every pixel represented in csmat.
    Returns
    -------
    final_graph : NBGraph
        The output csmat.
    """
    junctions = np.unique(junction_labels)[1:]  # discard 0, background
    for j, jloc in zip(junctions, junction_centroids):
        loc, stop = csmat.indptr[j], csmat.indptr[j + 1]
        neighbors = csmat.indices[loc:stop]
        neighbor_locations = pixel_indices[neighbors]
        distances = np.sqrt(np.sum((neighbor_locations - jloc) ** 2, axis=1))
        csmat.data[loc:stop] = distances
    tdata = csmat.T.tocsr().data
    csmat.data = np.maximum(csmat.data, tdata)

def _generateDegreesImage(skel):
    ndim = skel.ndim
    degree_kernel = np.ones((3,) * ndim)
    degree_kernel[(1,) * ndim] = 0  # remove centre pixel
    degree_image = ndi.convolve(skel.astype(int), degree_kernel,mode='constant') * skel
    return degree_image

def skeleton_to_csgraph(skel, degree_image, unique_junctions=True):
    # ensure we have a bool image, since we later use it for bool indexing
    skel = skel.astype(bool)
    ndim = skel.ndim

    pixel_indices = np.concatenate(([[0.] * ndim], np.transpose(np.nonzero(skel))), axis=0)
    skelint = np.zeros(skel.shape, dtype=int)
    skelint[tuple(pixel_indices.T.astype(int))] = np.arange(pixel_indices.shape[0])

    if unique_junctions:
        # group all connected junction nodes into "meganodes".
        junctions = degree_image > 2
        junction_ids = skelint[junctions]
        labeled_junctions, centroids = compute_centroids(junctions)
        labeled_junctions[junctions] = \
            junction_ids[labeled_junctions[junctions] - 1]
        skelint[junctions] = labeled_junctions[junctions]
        pixel_indices[np.unique(labeled_junctions)[1:]] = centroids

    num_edges = np.sum(degree_image)  # *2, which is how many we need to store
    skelint = pad(skelint, 0)  # pad image to prevent looparound errors
    steps, distances = raveled_steps_to_neighbors(skelint.shape, ndim)
    graph = _pixel_graph(skelint, steps, distances, num_edges)

    if unique_junctions:
        _uniquify_junctions(graph, pixel_indices, labeled_junctions, centroids)
    return graph, pixel_indices

def submatrix(M, idxs):
    """Return the outer-index product submatrix, `M[idxs, :][:, idxs]`.
    Parameters
    ----------
    M : scipy.sparse.spmatrix
        Input (square) matrix
    idxs : array of int
        The indices to subset. No index in `idxs` should exceed the
        number of rows of `M`.
    Returns
    -------
    Msub : scipy.sparse.spmatrix
        The subsetted matrix.
    Examples
    --------
    >>> Md = np.arange(16).reshape((4, 4))
    >>> M = sparse.csr_matrix(Md)
    >>> print(submatrix(M, [0, 2]).toarray())
    [[ 0  2]
     [ 8 10]]
    """
    Msub = M[idxs, :][:, idxs]
    return Msub

def compute_centroids(image):
    """Find the centroids of all nonzero connected blobs in `image`.
    Parameters
    ----------
    image : ndarray
        The input image.
    Returns
    -------
    label_image : ndarray of int
        The input image, with each connected region containing a different
        integer label.
    Examples
    --------
    >>> image = np.array([[1, 0, 1, 0, 0, 1, 1],
    ...                   [1, 0, 0, 1, 0, 0, 0]])
    >>> labels, centroids = compute_centroids(image)
    >>> print(labels)
    [[1 0 2 0 0 3 3]
     [1 0 0 2 0 0 0]]
    >>> centroids
    array([[0.5, 0. ],
           [0.5, 2.5],
           [0. , 5.5]])
    """
    connectivity = np.ones((3,) * image.ndim)
    labeled_image = ndi.label(image, connectivity)[0]
    nz = np.nonzero(labeled_image)
    nzpix = labeled_image[nz]
    sizes = np.bincount(nzpix)
    coords = np.transpose(nz)
    grouping = np.argsort(nzpix)
    sums = np.add.reduceat(coords[grouping], np.cumsum(sizes)[:-1])
    means = sums / sizes[1:, np.newaxis]
    return labeled_image, means

