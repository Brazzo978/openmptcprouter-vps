"""Exercise candidate preparation and the actual frozen guard without install.

The package builder and dpkg-deb are isolated fakes; no network or system
configuration is accessed. Run on Linux with python3 -m pytest -q <this file>.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.18+20261030-3k5'


@pytest.fixture
def prepared_lab(tmp_path):
    (tmp_path / 'run-vps-3k.sh').write_text((ROOT / 'run-vps-3k.sh').read_text())
    # The wrapper only syntax-checks the installer in prepare mode.
    (tmp_path / 'debian9-x86_64.sh').write_text('#!/bin/sh\nexit 0\n')
    (tmp_path / 'admin').mkdir()
    (tmp_path / 'debian').mkdir()
    (tmp_path / 'bin').mkdir()
    (tmp_path / 'admin/build-3k-deb.py').write_text(textwrap.dedent('''\
        import hashlib, json, os, pathlib, sys
        output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])
        version = '0.18+20261030-3k5'
        mode = os.environ.get('FAKE_BUILD_MODE', 'ok')
        fields = {'Package':'omr-vps-admin', 'Version':version, 'Architecture':'all'}
        if mode == 'wrong_package': fields['Package'] = 'other'
        if mode == 'wrong_version': fields['Version'] = '0.18+20261016-3k4'
        if mode == 'wrong_arch': fields['Architecture'] = 'amd64'
        blob = json.dumps(fields).encode()
        artifact = output / ('omr-vps-admin_' + version + '_all.deb')
        if mode != 'stale_only': artifact.write_bytes(blob)
        metadata = {'version': 'wrong' if mode == 'metadata_version' else version,
                    'sha256': '0' * 64 if mode == 'bad_sha' else hashlib.sha256(blob).hexdigest()}
        (output / 'omr-vps-admin-3k.json').write_text(json.dumps(metadata))
    '''))
    dpkg = tmp_path / 'bin/dpkg-deb'
    dpkg.write_text(textwrap.dedent('''\
        #!/usr/bin/env python3
        import json, pathlib, sys
        if len(sys.argv) != 4 or sys.argv[1] != '-f': sys.exit(2)
        try: print(json.loads(pathlib.Path(sys.argv[2]).read_text())[sys.argv[3]])
        except (OSError, ValueError, KeyError): sys.exit(1)
    '''))
    dpkg.chmod(0o755)
    env = os.environ.copy()
    env['PATH'] = str(tmp_path / 'bin') + os.pathsep + env['PATH']
    return tmp_path, env


def run_prepare(lab, mode):
    path, env = lab
    env['FAKE_BUILD_MODE'] = mode
    return subprocess.run(['sh', str(path / 'run-vps-3k.sh'), 'prepare'],
                          cwd=path, env=env, text=True, capture_output=True)


def test_prepares_only_verified_3k5(prepared_lab):
    result = run_prepare(prepared_lab, 'ok')
    assert result.returncode == 0, result.stderr
    assert 'package prepared' in result.stdout
    assert (prepared_lab[0] / 'debian' / f'omr-vps-admin_{VERSION}_all.deb').is_file()


@pytest.mark.parametrize('mode', ['stale_only', 'metadata_version', 'bad_sha', 'wrong_package', 'wrong_version', 'wrong_arch'])
def test_rejects_stale_or_invalid_candidate(prepared_lab, mode):
    path, _ = prepared_lab
    # A historical artifact must never make a missing 3k5 appear prepared.
    (path / 'debian/omr-vps-admin_0.18+20261016-3k4_all.deb').write_text('old release')
    result = run_prepare(prepared_lab, mode)
    assert result.returncode != 0
    assert 'package prepared' not in result.stdout


def actual_guard():
    source = (ROOT / 'debian9-x86_64.sh').read_text()
    begin = source.index('    if [ -z "${OMR_ADMIN_LOCAL_DEB:-}" ]')
    end = source.index('\n    fi', begin) + len('\n    fi')
    return textwrap.dedent(source[begin:end])


@pytest.mark.parametrize('change', ['none', 'old_version', 'wrong_package', 'wrong_version', 'wrong_arch', 'bad_sha'])
def test_frozen_guard_rejects_bad_metadata_and_digest(prepared_lab, change):
    path, env = prepared_lab
    fields = {'Package': 'omr-vps-admin', 'Version': VERSION, 'Architecture': 'all'}
    if change == 'wrong_package': fields['Package'] = 'other'
    if change == 'wrong_version': fields['Version'] = '0.18+20261016-3k4'
    if change == 'wrong_arch': fields['Architecture'] = 'amd64'
    blob = json.dumps(fields).encode()
    artifact = path / 'candidate.deb'
    artifact.write_bytes(blob)
    env['OMR_ADMIN_LOCAL_DEB'] = str(artifact)
    env['OMR_ADMIN_BINARY_VERSION'] = '0.18+20261016-3k4' if change == 'old_version' else VERSION
    env['OMR_ADMIN_EXPECTED_SHA256'] = '0' * 64 if change == 'bad_sha' else hashlib.sha256(blob).hexdigest()
    result = subprocess.run(['sh', '-c', actual_guard() + '\necho accepted\n'],
                            env=env, text=True, capture_output=True)
    assert (result.returncode == 0) == (change == 'none'), result.stderr
    assert ('accepted' in result.stdout) == (change == 'none')
