import os
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mock_config import mock_config

import bandersnatch.filter
import bandersnatch.storage
from bandersnatch.master import Master
from bandersnatch.mirror import BandersnatchMirror
from bandersnatch.package import Package


class TestAllowListProject(TestCase):
    """
    Tests for the bandersnatch filtering classes
    """

    tempdir = None
    cwd = None

    def setUp(self) -> None:
        self.cwd = os.getcwd()
        self.tempdir = TemporaryDirectory()
        bandersnatch.storage.loaded_storage_plugins = defaultdict(list)
        os.chdir(self.tempdir.name)

    def tearDown(self) -> None:
        if self.tempdir:
            assert self.cwd
            os.chdir(self.cwd)
            self.tempdir.cleanup()
            self.tempdir = None

    def test__plugin__loads__explicitly_enabled(self) -> None:
        mock_config(
            contents="""\
[plugins]
enabled =
    allowlist_project
"""
        )

        plugins = bandersnatch.filter.LoadedFilters().filter_project_plugins()
        names = [plugin.name for plugin in plugins]
        self.assertListEqual(names, ["allowlist_project"])
        self.assertEqual(len(plugins), 1)

    def test__plugin__loads__default(self) -> None:
        mock_config(
            """\
[mirror]
storage-backend = filesystem

[plugins]
"""
        )

        plugins = bandersnatch.filter.LoadedFilters().filter_project_plugins()
        names = [plugin.name for plugin in plugins]
        self.assertNotIn("allowlist_project", names)

    def test__filter__matches__package(self) -> None:
        mock_config(
            """\
[mirror]
storage-backend = filesystem

[plugins]
enabled =
    allowlist_project

[allowlist]
packages =
    foo
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        mirror.packages_to_sync = {"foo": ""}
        mirror._filter_packages()

        self.assertIn("foo", mirror.packages_to_sync.keys())

    def test__filter__nomatch_package(self) -> None:
        mock_config(
            """\
[mirror]
storage-backend = filesystem

[plugins]
enabled =
    allowlist_project

[allowlist]
packages =
    foo
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        mirror.packages_to_sync = {"foo": "", "foo2": ""}
        mirror._filter_packages()

        self.assertIn("foo", mirror.packages_to_sync.keys())
        self.assertNotIn("foo2", mirror.packages_to_sync.keys())

    def test__filter__name_only(self) -> None:
        mock_config(
            """\
[mirror]
storage-backend = filesystem

[plugins]
enabled =
    allowlist_project

[allowlist]
packages =
    foo==1.2.3
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        mirror.packages_to_sync = {"foo": "", "foo2": ""}
        mirror._filter_packages()

        self.assertIn("foo", mirror.packages_to_sync.keys())
        self.assertNotIn("foo2", mirror.packages_to_sync.keys())

    def test__filter__varying__specifiers(self) -> None:
        mock_config(
            """\
[mirror]
storage-backend = filesystem

[plugins]
enabled =
    allowlist_project

[allowlist]
packages =
    foo==1.2.3
    bar~=3.0,<=1.5
"""
        )
        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        mirror.packages_to_sync = {
            "foo": "",
            "bar": "",
            "snu": "",
        }
        mirror._filter_packages()

        self.assertEqual({"foo": "", "bar": ""}, mirror.packages_to_sync)

    def test__filter__commented__out(self) -> None:
        mock_config(
            """\
[mirror]
storage-backend = filesystem

[plugins]
enabled =
    allowlist_project

[allowlist]
packages =
    foo==1.2.3   # inline comment
#    bar
"""
        )
        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        mirror.packages_to_sync = {
            "foo": "",
            "bar": "",
            "snu": "",
        }
        mirror._filter_packages()

        self.assertEqual({"foo": ""}, mirror.packages_to_sync)


class TestAllowlistRelease(TestCase):
    """
    Tests for the bandersnatch filtering classes
    """

    tempdir = None
    cwd = None

    def setUp(self) -> None:
        self.cwd = os.getcwd()
        self.tempdir = TemporaryDirectory()
        os.chdir(self.tempdir.name)

    def tearDown(self) -> None:
        if self.tempdir:
            assert self.cwd
            os.chdir(self.cwd)
            self.tempdir.cleanup()
            self.tempdir = None

    def test__plugin__loads__explicitly_enabled(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_release
"""
        )

        plugins = bandersnatch.filter.LoadedFilters().filter_release_plugins()
        names = [plugin.name for plugin in plugins]
        self.assertListEqual(names, ["allowlist_release"])
        self.assertEqual(len(plugins), 1)

    def test__plugin__doesnt_load__explicitly__disabled(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_package
"""
        )

        plugins = bandersnatch.filter.LoadedFilters().filter_release_plugins()
        names = [plugin.name for plugin in plugins]
        self.assertNotIn("allowlist_release", names)

    def test__filter__matches__release(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_release
[allowlist]
packages =
    foo==1.2.0
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        pkg = Package("foo", 1)
        pkg._metadata = {
            "info": {"name": "foo"},
            "releases": {"1.2.0": {}, "1.2.1": {}},
        }

        pkg.filter_all_releases(mirror.filters.filter_release_plugins())

        self.assertEqual(pkg.releases, {"1.2.0": {}})

    def test__filter__matches__release__commented__inline(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_release
[allowlist]
packages =
    foo==1.2.0      # some inline comment
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        pkg = Package("foo", 1)
        pkg._metadata = {
            "info": {"name": "foo"},
            "releases": {"1.2.0": {}, "1.2.1": {}},
        }

        pkg.filter_all_releases(mirror.filters.filter_release_plugins())

        self.assertEqual(pkg.releases, {"1.2.0": {}})

    def test__dont__filter__prereleases(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_release
[allowlist]
packages =
    foo<=1.2.0
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        pkg = Package("foo", 1)
        pkg._metadata = {
            "info": {"name": "foo"},
            "releases": {
                "1.1.0a2": {},
                "1.1.1beta1": {},
                "1.2.0": {},
                "1.2.1": {},
                "1.2.2alpha3": {},
                "1.2.3rc1": {},
            },
        }

        pkg.filter_all_releases(mirror.filters.filter_release_plugins())

        self.assertEqual(pkg.releases, {"1.1.0a2": {}, "1.1.1beta1": {}, "1.2.0": {}})

    def test__casing__no__affect(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_release
[allowlist]
packages =
    Foo<=1.2.0
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        pkg = Package("foo", 1)
        pkg._metadata = {
            "info": {"name": "foo"},
            "releases": {"1.2.0": {}, "1.2.1": {}},
        }

        pkg.filter_all_releases(mirror.filters.filter_release_plugins())

        self.assertEqual(pkg.releases, {"1.2.0": {}})


class TestAllowlistRequirements(TestCase):
    """
    Tests for the bandersnatch filtering by requirements
    """

    tempdir = None
    cwd = None

    def setUp(self) -> None:
        self.cwd = os.getcwd()
        self.tempdir = TemporaryDirectory()
        os.chdir(self.tempdir.name)

    def tearDown(self) -> None:
        if self.tempdir:
            assert self.cwd
            os.chdir(self.cwd)
            self.tempdir.cleanup()
            self.tempdir = None

    def test__plugin__loads__explicitly_enabled(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    project_requirements_pinned
"""
        )

        plugins = bandersnatch.filter.LoadedFilters().filter_release_plugins()
        names = [plugin.name for plugin in plugins]
        self.assertListEqual(names, ["project_requirements_pinned"])
        self.assertEqual(len(plugins), 1)

    def test__plugin__doesnt_load__explicitly__disabled(self) -> None:
        mock_config(
            """\
[plugins]
enabled =
    allowlist_package
"""
        )

        plugins = bandersnatch.filter.LoadedFilters().filter_release_plugins()
        names = [plugin.name for plugin in plugins]
        self.assertNotIn("project_requirements", names)

    def test__filter__matches__release(self) -> None:

        with open(Path(self.tempdir.name) / "requirements.txt", "w") as fh:
            fh.write(
                """\
#    This is needed for workshop 1
#
foo==1.2.0             # via -r requirements.in            
"""
            )

        mock_config(
            f"""\
[plugins]
enabled =
    project_requirements
    project_requirements_pinned
[allowlist]
requirements_path = {self.tempdir.name}
requirements =
    requirements.txt
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))
        pkg = Package("foo", 1)
        pkg._metadata = {
            "info": {"name": "foo"},
            "releases": {"1.2.0": {}, "1.2.1": {}},
        }

        pkg.filter_all_releases(mirror.filters.filter_release_plugins())

        self.assertEqual({"1.2.0": {}}, pkg.releases)

    def test__filter__find_files(self) -> None:
        absolute_file_path = Path(self.tempdir.name) / "requirements.txt"
        with open(absolute_file_path, "w") as fh:
            fh.write(
                """\
#    This is needed for workshop 1
#
foo==1.2.0             # via -r requirements.in            
"""
            )

        mock_config(
            f"""\
[plugins]
enabled =
    project_requirements
[allowlist]
requirements =
    {absolute_file_path}
"""
        )

        mirror = BandersnatchMirror(Path("."), Master(url="https://foo.bar.com"))

        mirror.packages_to_sync = {
            "foo": "",
            "bar": "",
            "baz": "",
        }
        mirror._filter_packages()
        self.assertEqual({"foo": ""}, mirror.packages_to_sync)
