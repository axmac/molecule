#  Copyright (c) 2015-2017 Cisco Systems, Inc.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

import os

import m9dicts
import pytest

from molecule import config
from molecule import util
from molecule.command import base


@pytest.fixture()
def base_class(config_instance):
    class ExtendedBase(base.Base):
        def execute():
            pass

    return ExtendedBase


@pytest.fixture()
def base_instance(base_class, config_instance):
    return base_class(config_instance)


def test_config_private_member(base_instance):
    assert isinstance(base_instance._config, config.Config)


def test_load_config(temp_dir):
    inventory_file = os.path.join(temp_dir.strpath, 'inventory_file')
    util.write_file(inventory_file, 'foo: bar')

    assert {'foo': 'bar'} == base._load_config(inventory_file)


def test_load_config_returns_empty_dict_on_empty_file(temp_dir):
    inventory_file = os.path.join(temp_dir.strpath, 'inventory_file')
    util.write_file(inventory_file, '')

    assert {} == base._load_config(inventory_file)


def test_verify_configs(config_instance):
    configs = [config_instance]

    assert base._verify_configs(configs) is None


def test_verify_configs_raises_with_no_configs(patched_print_error):
    with pytest.raises(SystemExit) as e:
        base._verify_configs([])

    assert 1 == e.value.code

    msg = 'Unable to find a molecule.yml.  Exiting.'
    patched_print_error.assert_called_once_with(msg)


def test_verify_configs_raises_with_duplicate_configs(patched_print_error,
                                                      config_instance):
    with pytest.raises(SystemExit) as e:
        configs = [config_instance, config_instance]
        base._verify_configs(configs)

    assert 1 == e.value.code

    msg = "Duplicate scenario name 'default' found.  Exiting."
    patched_print_error.assert_called_once_with(msg)


def test_setup(mocker, config_instance):
    patched_provisioner_write_inventory = mocker.patch(
        'molecule.provisioner.ansible.Ansible.write_inventory')
    patched_provisioner_write_config = mocker.patch(
        'molecule.provisioner.ansible.Ansible.write_config')
    patched_provisioner_add_or_update_vars = mocker.patch(
        'molecule.provisioner.ansible.Ansible._add_or_update_vars')
    base._setup([config_instance])

    assert os.path.isdir(config_instance.ephemeral_directory)
    assert os.path.isdir(
        os.path.dirname(config_instance.provisioner.inventory_file))

    patched_provisioner_write_inventory.assert_called_once_with()
    patched_provisioner_write_config.assert_called_once_with()

    x = [mocker.call('host_vars'), mocker.call('group_vars')]
    assert x == patched_provisioner_add_or_update_vars.mock_calls


def test_get_configs(temp_dir, config_instance):
    molecule_file = config_instance.molecule_file
    data = config_instance.config
    data = m9dicts.convert_to(data)
    util.write_file(molecule_file, util.safe_dump(data))

    result = base.get_configs({}, {})
    assert 1 == len(result)
    assert isinstance(result, list)
    assert isinstance(result[0], config.Config)


def test_get_configs_calls_verify_configs(patched_verify_configs, temp_dir):
    base.get_configs({}, {})

    patched_verify_configs.assert_called_once_with([])


def test_get_configs_calls_setup(mocker, patched_verify_configs):
    m = mocker.patch('molecule.command.base._setup')
    base.get_configs({}, {})

    m.assert_called_once_with([])


def test_get_configs_filter_configs_for_scenario(
        mocker, patched_verify_configs, temp_dir):
    m = mocker.patch('molecule.command.base._filter_configs_for_scenario')
    base.get_configs({}, {'scenario_name': 'default'})

    m.assert_called_once_with('default', [])


def test_filter_configs_for_scenario(config_instance):
    configs = [config_instance, config_instance]

    result = base._filter_configs_for_scenario('default', configs)
    assert 2 == len(result)

    result = base._filter_configs_for_scenario('invalid', configs)
    assert [] == result
