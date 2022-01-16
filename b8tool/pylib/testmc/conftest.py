#   Nicer assertion error display for various testmc objects.
#   This is used for internal testing here as well as for projects using b8tool.
from    testmc.pytest  import pytest_assertrepr_compare

############################################################################
#   The following fixtures are part of the framework for unit testing
#   assembly language code in projects using b8tool. Typically these will
#   be added to the project by creating a src/conftest.py file containing:
#
#       from testmc.conftest import *
#

import  pytest
from    b8tool  import path

@pytest.fixture
def m(request):
    ''' A simulated machine with the object file loaded.

        The caller must define in its module a global variable ``Machine``
        which is the class of the CPU/machine simulator to instantiate.
        This is usually imported from one of the `testmc` submodules.

        If the module global ``object_files`` is defined, it will be read
        as a path (if `str`) or sequence of paths from which to load
        machine code via `Machine.load()`. Relative paths will be relative
        to `path.obj()`. Symbol values from earlier loads take preference
        over later loads.

        If the module global ``test_rig`` is defined it's assumed that a
        binary was built with ``b8tool asltest`` and it will be found and
        loaded based on the path from which the test module was loaded,
        using the portion relative to `B8_PROJDIR` under `path.ptobj()`.
        Symbol values from this load will be preferred over those
        previously loaded via ``object_files``.
    '''
    Machine = getattr(request.module, 'Machine')
    m = Machine()

    if hasattr(request.module, 'object_files'):
        objfiles = getattr(request.module, 'object_files')
        if isinstance(objfiles, str):   # because forgetting the comma is such
            objfiles = (objfiles,)      # an easy mistake for devs to make
        for f in objfiles:
            m.load(path.obj(f), mergestyle='prefcur', setPC=False)

    if hasattr(request.module, 'test_rig'):
        relmodpath = path.relproj(request.module.__file__)
        object_file = path.ptobj(relmodpath).with_suffix('.p')
        m.load(object_file, mergestyle='prefnew')

    return m

#   These rely on pytest running the m() fixture only once per test, even
#   though both these fixtures and the test itself use it. I'm not sure if
#   this behaviour is documented, but it makes sense given that pytest
#   maintains careful control over the scope (test/module/etc.) in which a
#   fixture is used.

@pytest.fixture
def S(m):
    ''' The `Machine.symtab` attribute of the machine object produced by
        the `m` fixture.
    '''
    return m.symtab

@pytest.fixture
def R(m):
    ''' The `Machine.registers` attribute of the machine object produced by
        the `m` fixture.
    '''
    return m.Registers

@pytest.fixture
def loadbios(m, S):
    ''' Return a function that loads a unit test BIOS and connects input
        and output streams.

        The first parameter is the BIOS system name; the BIOS is the object
        output of ``src/SYSNAME/bioscode.a??`. This assumes that the BIOS
        will define ``charinport`` and ``charoutport`` symbols, both set to
        the same value, that define the address in the memory map to set up
        to read and write for I/O to the streams below.

        `input`, `output` and the return values all are passed to and come
        from `testmc.generic.iomem.setiostreams()`, which is used to to
        create I/O streams for the console read and write functions of the
        BIOS. See that function's documentation for full details.

        If provided, `input` is typically a `bytes` to be read, but it may
        be anything with a `read(1)` method. `output` is typically left
        unset to have the framework provide a stream from which you can
        read the output generated by the code under test. A pair of
        ``istream, ostream`` (with ``istream`` usually ignored) is returned
        for the test to query.

        Sample usage::

            _, ostream = loadbios('tmc68', b'some input\n')
            ...
            assert b'Hello, world!' == ostream.getvalue()
    '''
    def loadbios(biosname, input=None, output=None):
        bioscode = path.obj('src', biosname, 'bioscode.p')
        m.load(bioscode, mergestyle='prefcur', setPC=False)
        assert S['charinport'] == S['charoutport']
        return m.setiostreams(S.charinport, input, output)
    return loadbios

