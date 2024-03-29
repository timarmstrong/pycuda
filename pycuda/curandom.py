from __future__ import division

import numpy as np
import pycuda.compiler
import pycuda.driver as drv
import pycuda.gpuarray as array
from pytools import memoize_method



# {{{ MD5-based random number generation

md5_code = """
/*
 **********************************************************************
 ** Copyright (C) 1990, RSA Data Security, Inc. All rights reserved. **
 **                                                                  **
 ** License to copy and use this software is granted provided that   **
 ** it is identified as the "RSA Data Security, Inc. MD5 Message     **
 ** Digest Algorithm" in all material mentioning or referencing this **
 ** software or this function.                                       **
 **                                                                  **
 ** License is also granted to make and use derivative works         **
 ** provided that such works are identified as "derived from the RSA **
 ** Data Security, Inc. MD5 Message Digest Algorithm" in all         **
 ** material mentioning or referencing the derived work.             **
 **                                                                  **
 ** RSA Data Security, Inc. makes no representations concerning      **
 ** either the merchantability of this software or the suitability   **
 ** of this software for any particular purpose.  It is provided "as **
 ** is" without express or implied warranty of any kind.             **
 **                                                                  **
 ** These notices must be retained in any copies of any part of this **
 ** documentation and/or software.                                   **
 **********************************************************************
 */

/* F, G and H are basic MD5 functions: selection, majority, parity */
#define F(x, y, z) (((x) & (y)) | ((~x) & (z)))
#define G(x, y, z) (((x) & (z)) | ((y) & (~z)))
#define H(x, y, z) ((x) ^ (y) ^ (z))
#define I(x, y, z) ((y) ^ ((x) | (~z)))

/* ROTATE_LEFT rotates x left n bits */
#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32-(n))))

/* FF, GG, HH, and II transformations for rounds 1, 2, 3, and 4 */
/* Rotation is separate from addition to prevent recomputation */
#define FF(a, b, c, d, x, s, ac) \
  {(a) += F ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }
#define GG(a, b, c, d, x, s, ac) \
  {(a) += G ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }
#define HH(a, b, c, d, x, s, ac) \
  {(a) += H ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }
#define II(a, b, c, d, x, s, ac) \
  {(a) += I ((b), (c), (d)) + (x) + (ac); \
   (a) = ROTATE_LEFT ((a), (s)); \
   (a) += (b); \
  }

#define X0 threadIdx.x
#define X1 threadIdx.y
#define X2 threadIdx.z
#define X3 blockIdx.x
#define X4 blockIdx.y
#define X5 blockIdx.z
#define X6 seed
#define X7 i
#define X8 n
#define X9  blockDim.x
#define X10 blockDim.y
#define X11 blockDim.z
#define X12 gridDim.x
#define X13 gridDim.y
#define X14 gridDim.z
#define X15 0

  unsigned int a = 0x67452301;
  unsigned int b = 0xefcdab89;
  unsigned int c = 0x98badcfe;
  unsigned int d = 0x10325476;

  /* Round 1 */
#define S11 7
#define S12 12
#define S13 17
#define S14 22
  FF ( a, b, c, d, X0 , S11, 3614090360); /* 1 */
  FF ( d, a, b, c, X1 , S12, 3905402710); /* 2 */
  FF ( c, d, a, b, X2 , S13,  606105819); /* 3 */
  FF ( b, c, d, a, X3 , S14, 3250441966); /* 4 */
  FF ( a, b, c, d, X4 , S11, 4118548399); /* 5 */
  FF ( d, a, b, c, X5 , S12, 1200080426); /* 6 */
  FF ( c, d, a, b, X6 , S13, 2821735955); /* 7 */
  FF ( b, c, d, a, X7 , S14, 4249261313); /* 8 */
  FF ( a, b, c, d, X8 , S11, 1770035416); /* 9 */
  FF ( d, a, b, c, X9 , S12, 2336552879); /* 10 */
  FF ( c, d, a, b, X10, S13, 4294925233); /* 11 */
  FF ( b, c, d, a, X11, S14, 2304563134); /* 12 */
  FF ( a, b, c, d, X12, S11, 1804603682); /* 13 */
  FF ( d, a, b, c, X13, S12, 4254626195); /* 14 */
  FF ( c, d, a, b, X14, S13, 2792965006); /* 15 */
  FF ( b, c, d, a, X15, S14, 1236535329); /* 16 */

  /* Round 2 */
#define S21 5
#define S22 9
#define S23 14
#define S24 20
  GG ( a, b, c, d, X1 , S21, 4129170786); /* 17 */
  GG ( d, a, b, c, X6 , S22, 3225465664); /* 18 */
  GG ( c, d, a, b, X11, S23,  643717713); /* 19 */
  GG ( b, c, d, a, X0 , S24, 3921069994); /* 20 */
  GG ( a, b, c, d, X5 , S21, 3593408605); /* 21 */
  GG ( d, a, b, c, X10, S22,   38016083); /* 22 */
  GG ( c, d, a, b, X15, S23, 3634488961); /* 23 */
  GG ( b, c, d, a, X4 , S24, 3889429448); /* 24 */
  GG ( a, b, c, d, X9 , S21,  568446438); /* 25 */
  GG ( d, a, b, c, X14, S22, 3275163606); /* 26 */
  GG ( c, d, a, b, X3 , S23, 4107603335); /* 27 */
  GG ( b, c, d, a, X8 , S24, 1163531501); /* 28 */
  GG ( a, b, c, d, X13, S21, 2850285829); /* 29 */
  GG ( d, a, b, c, X2 , S22, 4243563512); /* 30 */
  GG ( c, d, a, b, X7 , S23, 1735328473); /* 31 */
  GG ( b, c, d, a, X12, S24, 2368359562); /* 32 */

  /* Round 3 */
#define S31 4
#define S32 11
#define S33 16
#define S34 23
  HH ( a, b, c, d, X5 , S31, 4294588738); /* 33 */
  HH ( d, a, b, c, X8 , S32, 2272392833); /* 34 */
  HH ( c, d, a, b, X11, S33, 1839030562); /* 35 */
  HH ( b, c, d, a, X14, S34, 4259657740); /* 36 */
  HH ( a, b, c, d, X1 , S31, 2763975236); /* 37 */
  HH ( d, a, b, c, X4 , S32, 1272893353); /* 38 */
  HH ( c, d, a, b, X7 , S33, 4139469664); /* 39 */
  HH ( b, c, d, a, X10, S34, 3200236656); /* 40 */
  HH ( a, b, c, d, X13, S31,  681279174); /* 41 */
  HH ( d, a, b, c, X0 , S32, 3936430074); /* 42 */
  HH ( c, d, a, b, X3 , S33, 3572445317); /* 43 */
  HH ( b, c, d, a, X6 , S34,   76029189); /* 44 */
  HH ( a, b, c, d, X9 , S31, 3654602809); /* 45 */
  HH ( d, a, b, c, X12, S32, 3873151461); /* 46 */
  HH ( c, d, a, b, X15, S33,  530742520); /* 47 */
  HH ( b, c, d, a, X2 , S34, 3299628645); /* 48 */

  /* Round 4 */
#define S41 6
#define S42 10
#define S43 15
#define S44 21
  II ( a, b, c, d, X0 , S41, 4096336452); /* 49 */
  II ( d, a, b, c, X7 , S42, 1126891415); /* 50 */
  II ( c, d, a, b, X14, S43, 2878612391); /* 51 */
  II ( b, c, d, a, X5 , S44, 4237533241); /* 52 */
  II ( a, b, c, d, X12, S41, 1700485571); /* 53 */
  II ( d, a, b, c, X3 , S42, 2399980690); /* 54 */
  II ( c, d, a, b, X10, S43, 4293915773); /* 55 */
  II ( b, c, d, a, X1 , S44, 2240044497); /* 56 */
  II ( a, b, c, d, X8 , S41, 1873313359); /* 57 */
  II ( d, a, b, c, X15, S42, 4264355552); /* 58 */
  II ( c, d, a, b, X6 , S43, 2734768916); /* 59 */
  II ( b, c, d, a, X13, S44, 1309151649); /* 60 */
  II ( a, b, c, d, X4 , S41, 4149444226); /* 61 */
  II ( d, a, b, c, X11, S42, 3174756917); /* 62 */
  II ( c, d, a, b, X2 , S43,  718787259); /* 63 */
  II ( b, c, d, a, X9 , S44, 3951481745); /* 64 */

  a += 0x67452301;
  b += 0xefcdab89;
  c += 0x98badcfe;
  d += 0x10325476;
"""




def rand(shape, dtype=np.float32, stream=None):
    from pycuda.gpuarray import GPUArray
    from pycuda.elementwise import get_elwise_kernel

    result = GPUArray(shape, dtype)

    if dtype == np.float32:
        func = get_elwise_kernel(
            "float *dest, unsigned int seed",
            md5_code + """
            #define POW_2_M32 (1/4294967296.0f)
            dest[i] = a*POW_2_M32;
            if ((i += total_threads) < n)
                dest[i] = b*POW_2_M32;
            if ((i += total_threads) < n)
                dest[i] = c*POW_2_M32;
            if ((i += total_threads) < n)
                dest[i] = d*POW_2_M32;
            """,
            "md5_rng_float")
    elif dtype == np.float64:
        func = get_elwise_kernel(
            "double *dest, unsigned int seed",
            md5_code + """
            #define POW_2_M32 (1/4294967296.0)
            #define POW_2_M64 (1/18446744073709551616.)

            dest[i] = a*POW_2_M32 + b*POW_2_M64;

            if ((i += total_threads) < n)
            {
              dest[i] = c*POW_2_M32 + d*POW_2_M64;
            }
            """,
            "md5_rng_float")
    elif dtype in [np.int32, np.uint32]:
        func = get_elwise_kernel(
            "unsigned int *dest, unsigned int seed",
            md5_code + """
            dest[i] = a;
            if ((i += total_threads) < n)
                dest[i] = b;
            if ((i += total_threads) < n)
                dest[i] = c;
            if ((i += total_threads) < n)
                dest[i] = d;
            """,
            "md5_rng_int")
    else:
        raise NotImplementedError;

    func.prepared_async_call(result._grid, result._block, stream,
            result.gpudata, np.random.randint(2**31-1), result.size)

    return result

# }}}

# {{{ CURAND wrapper

try:
    import pycuda._driver as _curand # used to be separate module
except ImportError:
    def get_curand_version():
        return None
else:
    get_curand_version = _curand.get_curand_version

if get_curand_version() >= (3, 2, 0):
    direction_vector_set = _curand.direction_vector_set
    _get_direction_vectors = _curand._get_direction_vectors

if get_curand_version() >= (4, 0, 0):
    _get_scramble_constants32 = _curand._get_scramble_constants32
    _get_scramble_constants64 = _curand._get_scramble_constants64

# {{{ Base class

gen_template = """
__global__ void %(name)s(%(state_type)s *s, %(out_type)s *d, const int n)
{
  const int tidx = blockIdx.x*blockDim.x+threadIdx.x;
  const int delta = blockDim.x*gridDim.x;
  for (int idx = tidx; idx < n; idx += delta)
    d[idx] = curand%(suffix)s(&s[tidx]);
}
"""

random_source = """
// Uses C++ features (templates); do not surround with extern C
#include <curand_kernel.h>

extern "C"
{

%(generators)s

}
"""

random_skip_ahead32_source = """
extern "C" {
__global__ void skip_ahead(%(state_type)s *s, const int n, const unsigned int skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead(skip, &s[idx]);
}

__global__ void skip_ahead_array(%(state_type)s *s, const int n, const unsigned int *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead(skip[idx], &s[idx]);
}
}
"""

random_skip_ahead64_source = """
extern "C" {
__global__ void skip_ahead(%(state_type)s *s, const int n, const unsigned long long skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead(skip, &s[idx]);
}

__global__ void skip_ahead_array(%(state_type)s *s, const int n, const unsigned long long *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead(skip[idx], &s[idx]);
}
}
"""



class _RandomNumberGeneratorBase(object):
    """
    Class surrounding CURAND kernels from CUDA 3.2.
    It allows for generating random numbers with uniform
    and normal probability function of various types.
    """

    gen_info = [
        ("uniform_int", "int", ""),
        ("uniform_float", "float", "_uniform"),
        ("uniform_double", "double", "_uniform_double"),
        ("normal_float", "float", "_normal"),
        ("normal_double", "double", "_normal_double"),
        ("normal_float2", "float2", "_normal2"),
        ("normal_double2", "double2", "_normal2_double"),
        ]

    def __init__(self, state_type, additional_source):
        if get_curand_version() < (3, 2, 0):
            raise EnvironmentError("Need at least CUDA 3.2")

        # Max 256 threads on ION during preparing
        # Need to limit number of threads. If not there is failed execution:
        # pycuda._driver.LaunchError: cuLaunchGrid failed: launch out of resources

        dev = drv.Context.get_device()

        self.block_count = dev.get_attribute(
            pycuda.driver.device_attribute.MULTIPROCESSOR_COUNT)

        from pycuda.characterize import has_double_support

        def do_generate(out_type):
            result = True
            if "double" in out_type:
                result = result and has_double_support()
            if "2" in out_type:
                result = result and self.has_box_muller
            return result

        my_generators = [
                (name, out_type, suffix)
                for name, out_type, suffix in self.gen_info
                if do_generate(out_type)]

        generator_sources = [
                gen_template % {
                    "name":name, "out_type":out_type, "suffix": suffix,
                    "state_type": state_type, }
                for name, out_type, suffix in my_generators]

        source = (random_source + additional_source) % {
            "state_type": state_type,
            "generators": "\n".join(generator_sources)}

        # store in instance to let subclass constructors get to it.
        self.module = module = pycuda.compiler.SourceModule(source, no_extern_c=True)

        self.generators = {}
        for name, out_type, suffix  in my_generators:
            gen_func = module.get_function(name)
            gen_func.prepare("PPi")
            self.generators[name] = gen_func

        self.skip_ahead = module.get_function("skip_ahead")
        self.skip_ahead.prepare("Pii")
        self.skip_ahead_array = module.get_function("skip_ahead_array")
        self.skip_ahead_array.prepare("PiP")

        self.state_type = state_type
        self._state = None

    def _kernels(self):
        return (
                list(self.generators.itervalues())
                + [self.skip_ahead, self.skip_ahead_array])

    @property
    @memoize_method
    def generators_per_block(self):
        return min(kernel.max_threads_per_block
                for kernel in self._kernels())

    @property
    def state(self):
        if self._state is None:
            from pycuda.characterize import sizeof
            data_type_size = sizeof(self.state_type, "#include <curand_kernel.h>")

            self._state = drv.mem_alloc(
                self.block_count * self.generators_per_block * data_type_size)

        return self._state

    def fill_uniform(self, data, stream=None):
        if data.dtype == np.float32:
            func = self.generators["uniform_float"]
        elif data.dtype == np.float64:
            func = self.generators["uniform_double"]
        elif data.dtype in [np.int, np.int32, np.uint32]:
            func = self.generators["uniform_int"]
        else:
            raise NotImplementedError

        func.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, data.gpudata, data.size)

    def fill_normal(self, data, stream=None):
        if data.dtype == np.float32:
            func_name = "normal_float"
        elif data.dtype == np.float64:
            func_name = "normal_double"
        else:
            raise NotImplementedError

        data_size = data.size
        if self.has_box_muller and data_size % 2 == 0:
            func_name += "2"
            data_size /= 2

        func = self.generators[func_name]

        func.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, data.gpudata, data_size)

    def gen_uniform(self, shape, dtype, stream=None):
        result = array.empty(shape, dtype)
        self.fill_uniform(result, stream)
        return result

    def gen_normal(self, shape, dtype, stream=None):
        result = array.empty(shape, dtype)
        self.fill_normal(result, stream)
        return result

    def call_skip_ahead(self, i, stream=None):
        self.skip_ahead.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, self.generators_per_block, i)

    def call_skip_ahead_array(self, i, stream=None):
        self.skip_ahead_array.prepared_async_call(
                (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                self.state, self.generators_per_block, i.gpudata)

# }}}

# {{{ XORWOW RNG

def seed_getter_uniform(N):
    result = pycuda.gpuarray.empty([N], np.int32)
    value = random.randint(0, 2**31-1)
    return result.fill(value)

def seed_getter_unique(N):
    result = np.random.randint(0, 2**31-1, N).astype(np.int32)
    return pycuda.gpuarray.to_gpu(result)

xorwow_random_source = """
extern "C" {
__global__ void prepare_with_seeds(curandStateXORWOW *s, const int n,
  const int *seed, const int offset)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(seed[id], threadIdx.x, offset, &s[id]);
}

__global__ void skip_ahead_sequence(%(state_type)s *s, const int n, const unsigned int skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
    skipahead_sequence(skip, &s[idx]);
}

__global__ void skip_ahead_sequence_array(%(state_type)s *s, const int n, const unsigned int *skip)
{
  const int idx = blockIdx.x*blockDim.x+threadIdx.x;
  if (idx < n)
      skipahead_sequence(skip[idx], &s[idx]);
}
}
"""


if get_curand_version() >= (3, 2, 0):
    class XORWOWRandomNumberGenerator(_RandomNumberGeneratorBase):
        has_box_muller = True

        def __init__(self, seed_getter=None, offset=0):
            """
            :arg seed_getter: a function that, given an integer count, will yield an `int32`
              :class:`GPUArray` of seeds.
            """

            super(XORWOWRandomNumberGenerator, self).__init__(
                'curandStateXORWOW', xorwow_random_source+random_skip_ahead64_source)

            if seed_getter is None:
                seed = array.to_gpu(
                        np.asarray(
                            np.random.random_integers(
                                0, (1 << 31) - 2, self.generators_per_block),
                            dtype=np.int32))
            else:
                seed = seed_getter(self.generators_per_block)

            if not (isinstance(seed, pycuda.gpuarray.GPUArray)
                    and seed.dtype == np.int32
                    and seed.size == self.generators_per_block):
                raise TypeError("seed must be GPUArray of integers of right length")

            p = self.module.get_function("prepare_with_seeds")
            p.prepare("PiPi")
            self.skip_ahead_sequence = self.module.get_function("skip_ahead_sequence")
            self.skip_ahead_sequence.prepare("Pii")
            self.skip_ahead_sequence_array = self.module.get_function("skip_ahead_sequence_array")
            self.skip_ahead_sequence_array.prepare("PiP")

            from pycuda.characterize import has_stack
            has_stack = has_stack()

            if has_stack:
                prev_stack_size = drv.Context.get_limit(drv.limit.STACK_SIZE)

            try:
                if has_stack:
                    drv.Context.set_limit(drv.limit.STACK_SIZE, 1<<14) # 16k
                try:
                    dev = drv.Context.get_device()
                    p.prepared_call(
                            (self.block_count, 1), (self.generators_per_block, 1, 1), self.state,
                            self.block_count * self.generators_per_block, seed.gpudata, offset)
                except drv.LaunchError:
                    raise ValueError("Initialisation failed. Decrease number of threads.")

            finally:
                if has_stack:
                    drv.Context.set_limit(drv.limit.STACK_SIZE, prev_stack_size)

        def call_skip_ahead_sequence(self, i, stream=None):
            self.skip_ahead_sequence.prepared_async_call(
                    (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                    self.state, self.generators_per_block, i)

        def call_skip_ahead_sequence_array(self, i, stream=None):
            self.skip_ahead_sequence_array.prepared_async_call(
                    (self.block_count, 1), (self.generators_per_block, 1, 1), stream,
                    self.state, self.generators_per_block, i.gpudata)

        def _kernels(self):
            return (_RandomNumberGeneratorBase._kernels(self)
                    + [self.module.get_function("prepare_with_seeds")]
                    + [self.module.get_function("skip_ahead_sequence"),
                       self.module.get_function("skip_ahead_sequence_array")])

# }}}

# {{{ Sobol RNG

def generate_direction_vectors(count, direction=None):
    if get_curand_version() >= (4, 0, 0):
        if direction == direction_vector_set.VECTOR_64 or \
            direction == direction_vector_set.SCRAMBLED_VECTOR_64:
            result = np.empty((count, 64), dtype=np.uint64)
        else:
            result = np.empty((count, 32), dtype=np.uint32)
    else:
        result = np.empty((count, 32), dtype=np.uint32)
    _get_direction_vectors(direction, result, count)
    return pycuda.gpuarray.to_gpu(result)

if get_curand_version() >= (4, 0, 0):
    def generate_scramble_constants32(count):
        result = np.empty((count, ), dtype=np.uint32)
        _get_scramble_constants32(result, count)
        return pycuda.gpuarray.to_gpu(result)

    def generate_scramble_constants64(count):
        result = np.empty((count, ), dtype=np.uint64)
        _get_scramble_constants64(result, count)
        return pycuda.gpuarray.to_gpu(result)

class _SobolRandomNumberGeneratorBase(_RandomNumberGeneratorBase):
    """
    Class surrounding CURAND kernels from CUDA 3.2.
    It allows for generating quasi-random numbers with uniform
    and normal probability function of type int, float, and double.
    """

    has_box_muller = False

    def __init__(self, dir_vector, dir_vector_dtype, dir_vector_size,
        dir_vector_set, offset, state_type, sobol_random_source):
        super(_SobolRandomNumberGeneratorBase, self).__init__(state_type,
            sobol_random_source)

        if dir_vector is None:
            dir_vector = generate_direction_vectors(
                self.block_count * self.generators_per_block, dir_vector_set)

        if not (isinstance(dir_vector, pycuda.gpuarray.GPUArray)
                and dir_vector.dtype == dir_vector_dtype
                and dir_vector.shape == (self.block_count * self.generators_per_block, dir_vector_size)):
            raise TypeError("seed must be GPUArray of integers of right length")

        p = self.module.get_function("prepare")
        p.prepare("PiPi")

        from pycuda.characterize import has_stack
        has_stack = has_stack()

        if has_stack:
            prev_stack_size = drv.Context.get_limit(drv.limit.STACK_SIZE)

        try:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, 1<<14) # 16k
            try:
                p.prepared_call((2 * self.block_count, 1), (self.generators_per_block // 2, 1, 1),
                    self.state, self.block_count * self.generators_per_block,
                    dir_vector.gpudata, offset)
            except drv.LaunchError:
                raise ValueError("Initialisation failed. Decrease number of threads.")

        finally:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, prev_stack_size)

    def _kernels(self):
        return (_RandomNumberGeneratorBase._kernels(self)
                + [self.module.get_function("prepare")])

class _ScrambledSobolRandomNumberGeneratorBase(_RandomNumberGeneratorBase):
    """
    Class surrounding CURAND kernels from CUDA 4.0.
    It allows for generating quasi-random numbers with uniform
    and normal probability function of type int, float, and double.
    """

    has_box_muller = False

    def __init__(self, dir_vector, dir_vector_dtype, dir_vector_size,
        dir_vector_set, scramble_vector, scramble_vector_function,
        offset, state_type, sobol_random_source):
        super(_ScrambledSobolRandomNumberGeneratorBase, self).__init__(state_type,
            sobol_random_source)

        if dir_vector is None:
            dir_vector = generate_direction_vectors(
                self.block_count * self.generators_per_block,
                dir_vector_set)

        if scramble_vector is None:
            scramble_vector = scramble_vector_function(
                self.block_count * self.generators_per_block)

        if not (isinstance(dir_vector, pycuda.gpuarray.GPUArray)
                and dir_vector.dtype == dir_vector_dtype
                and dir_vector.shape == (self.block_count * self.generators_per_block, dir_vector_size)):
            raise TypeError("seed must be GPUArray of integers of right length")

        if not (isinstance(scramble_vector, pycuda.gpuarray.GPUArray)
                and scramble_vector.dtype == dir_vector_dtype
                and scramble_vector.shape == (self.block_count * self.generators_per_block, )):
            raise TypeError("scramble must be GPUArray of integers of right length")

        p = self.module.get_function("prepare")
        p.prepare("PiPPi")

        from pycuda.characterize import has_stack
        has_stack = has_stack()

        if has_stack:
            prev_stack_size = drv.Context.get_limit(drv.limit.STACK_SIZE)

        try:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, 1<<14) # 16k
            try:
                p.prepared_call((2 * self.block_count, 1), (self.generators_per_block // 2, 1, 1),
                    self.state, self.block_count * self.generators_per_block,
                    dir_vector.gpudata, scramble_vector.gpudata, offset)
            except drv.LaunchError:
                raise ValueError("Initialisation failed. Decrease number of threads.")

        finally:
            if has_stack:
                drv.Context.set_limit(drv.limit.STACK_SIZE, prev_stack_size)

    def _kernels(self):
        return (_RandomNumberGeneratorBase._kernels(self)
                + [self.module.get_function("prepare")])

sobol32_random_source = """
extern "C" {
__global__ void prepare(curandStateSobol32 *s, const int n,
    curandDirectionVectors32_t *v, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], o, &s[id]);
}
}
"""

if get_curand_version() >= (3, 2, 0):
    class Sobol32RandomNumberGenerator(_SobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 3.2.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, offset=0):
            super(Sobol32RandomNumberGenerator, self).__init__(dir_vector,
                np.uint32, 32, direction_vector_set.VECTOR_32, offset,
                'curandStateSobol32', sobol32_random_source+random_skip_ahead32_source)

scrambledsobol32_random_source = """
extern "C" {
__global__ void prepare(curandStateScrambledSobol32 *s, const int n,
    curandDirectionVectors32_t *v, unsigned int *scramble, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], scramble[id], o, &s[id]);
}
}
"""

if get_curand_version() >= (4, 0, 0):
    class ScrambledSobol32RandomNumberGenerator(_ScrambledSobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 4.0.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, scramble_vector=None, offset=0):
            super(ScrambledSobol32RandomNumberGenerator, self).__init__(dir_vector,
                np.uint32, 32, direction_vector_set.SCRAMBLED_VECTOR_32,
                scramble_vector, generate_scramble_constants32, offset,
                'curandStateScrambledSobol32', scrambledsobol32_random_source+random_skip_ahead32_source)

sobol64_random_source = """
extern "C" {
__global__ void prepare(curandStateSobol64 *s, const int n, curandDirectionVectors64_t *v,
    const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], o, &s[id]);
}
}
"""


if get_curand_version() >= (4, 0, 0):
    class Sobol64RandomNumberGenerator(_SobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 4.0.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, offset=0):
            super(Sobol64RandomNumberGenerator, self).__init__(dir_vector,
                np.uint64, 64, direction_vector_set.VECTOR_64, offset,
                'curandStateSobol64', sobol64_random_source+random_skip_ahead64_source)

scrambledsobol64_random_source = """
extern "C" {
__global__ void prepare(curandStateScrambledSobol64 *s, const int n,
    curandDirectionVectors64_t *v, unsigned long long *scramble, const unsigned int o)
{
  const int id = blockIdx.x*blockDim.x+threadIdx.x;
  if (id < n)
    curand_init(v[id], scramble[id], o, &s[id]);
}
}
"""

if get_curand_version() >= (4, 0, 0):
    class ScrambledSobol64RandomNumberGenerator(_ScrambledSobolRandomNumberGeneratorBase):
        """
        Class surrounding CURAND kernels from CUDA 4.0.
        It allows for generating quasi-random numbers with uniform
        and normal probability function of type int, float, and double.
        """

        def __init__(self, dir_vector=None, scramble_vector=None, offset=0):
            super(ScrambledSobol64RandomNumberGenerator, self).__init__(dir_vector,
                np.uint64, 64, direction_vector_set.SCRAMBLED_VECTOR_64,
                scramble_vector, generate_scramble_constants64, offset,
                'curandStateScrambledSobol64', scrambledsobol64_random_source+random_skip_ahead64_source)

# }}}

# }}}





# vim: foldmethod=marker
