#  Copyright (c) 2014 Maximilien Riehl <max@riehl.io>
#  This work is free. You can redistribute it and/or modify it under the
#  terms of the Do What The Fuck You Want To Public License, Version 2,
#  as published by Sam Hocevar. See the COPYING.wtfpl file for more details.
#

from unittest import TestCase
import re

from mock import patch, call, Mock

from isphere.command import VSphereREPL


class PatternTests(TestCase):

    def setUp(self):
        self.repl = VSphereREPL()

    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_yield_one_vm_when_pattern_matches(self, list_cached_vms):
        list_cached_vms.return_value = ["vm-1", "vm-2"]

        actual_matches = [match for match in self.repl.yield_patterns([re.compile("vm-1")])]

        self.assertEqual(actual_matches, ["vm-1"])

    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_yield_empty_list_when_pattern_does_not_match(self, list_cached_vms):
        list_cached_vms.return_value = ["vm-1", "vm-2"]

        actual_matches = [match for match in self.repl.yield_patterns([re.compile("^does-not-match$")])]

        self.assertEqual(actual_matches, [])

    def test_should_yield_empty_list_when_no_vms_cached(self):
        actual_matches = [match for match in self.repl.yield_patterns([re.compile("any-pattern")])]

        self.assertEqual(actual_matches, [])

    @patch("isphere.command._input")
    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_yield_all_vms_when_no_when_patterns_given_and_user_confirms(self, list_cached_vms, _input):
        list_cached_vms.return_value = ["vm-1", "vm-2", "other-vm"]
        _input.return_value = "y"

        actual_matches = [match for match in self.repl.compile_and_yield_patterns("")]

        self.assertEqual(actual_matches, ["vm-1", "vm-2", "other-vm"])

    @patch("isphere.command._input")
    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_return_empty_list_when_no_when_patterns_given_and_user_refuses(self, list_cached_vms, _input):
        list_cached_vms.return_value = ["vm-1", "vm-2", "other-vm"]
        _input.return_value = "N"

        actual_matches = [match for match in self.repl.compile_and_yield_patterns("")]

        self.assertEqual(actual_matches, [])

    @patch("isphere.command._input")
    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_return_empty_list_when_no_when_patterns_given_and_user_defaults(self, list_cached_vms, _input):
        list_cached_vms.return_value = ["vm-1", "vm-2", "other-vm"]
        _input.return_value = ""

        actual_matches = [match for match in self.repl.compile_and_yield_patterns("")]

        self.assertEqual(actual_matches, [])

    @patch("isphere.command._input")
    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_return_empty_list_when_no_when_patterns_given_and_user_writes_something_else(self, list_cached_vms, _input):
        list_cached_vms.return_value = ["vm-1", "vm-2", "other-vm"]
        _input.return_value = "?"

        actual_matches = [match for match in self.repl.compile_and_yield_patterns("")]

        self.assertEqual(actual_matches, [])

    @patch("isphere.command._input")
    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_yield_one_vm_when_pattern_given(self, list_cached_vms, _):
        list_cached_vms.return_value = ["vm-1", "vm-2", "other-vm"]

        actual_matches = [match for match in self.repl.compile_and_yield_patterns("other.*")]

        self.assertEqual(actual_matches, ["other-vm"])

    @patch("isphere.command._input")
    @patch("isphere.command.CachingVSphere.list_cached_vms")
    def test_should_yield_several_vms_when_ored_patterns_given(self, list_cached_vms, _):
        list_cached_vms.return_value = ["vm-1", "vm-2", "other-vm", "my-vm-name"]

        actual_matches = [match for match in self.repl.compile_and_yield_patterns("other.* ..-2 my-vm")]

        self.assertEqual(actual_matches, ["vm-2", "other-vm", "my-vm-name"])


class VSphereREPLTests(TestCase):

    def setUp(self):
        self.repl = VSphereREPL()
        self.print_patcher = patch("isphere.command.print", create=True)
        self.mock_print = self.print_patcher.start()

        self.vm_names_patcher = patch("isphere.command.VSphereREPL.compile_and_yield_patterns")
        self.vm_names = self.vm_names_patcher.start()

    def tearDown(self):
        self.print_patcher.stop()
        self.vm_names_patcher.stop()

    @patch("isphere.command.CachingVSphere.retrieve")
    def test_should_retrieve_vm_from_cache(self, cache_retrieve):
        self.assertEqual(self.repl.retrieve("any-vm-name"), cache_retrieve.return_value)

    def test_should_list_matching_vms(self):
        self.vm_names.return_value = ["any-host-1", "any-host-2"]

        self.repl.do_list("any-host")

        self.assertEqual(self.mock_print.call_args_list,
                         [call('any-host-1'), call('any-host-2')])

    @patch("isphere.command.CachingVSphere.retrieve")
    def test_should_print_info_for_matching_vms(self, cache_retrieve):
        self.vm_names.return_value = ["any-host-1"]
        mock_vm = Mock(
            config=Mock(
                uuid="any-uuid",
                guestId="any-id",
                version="any-version",
                guestFullName="any-full-name",
                hardware=Mock(numCPU=2,
                              memoryMB=2048,
                              )))
        mock_vm.guest.guestState = "any-guest-state"
        mock_vm.name = "any-name"
        mock_vm.get_esx_host.return_value.name = "any-esx-name"
        cache_retrieve.return_value = mock_vm

        self.repl.do_info("any-host-1")

        self.assertEqual(self.mock_print.call_args_list,
                         [
                             call('----------------------------------------------------------------------'),
                             call("Name: any-name"),
                             call("Host: any-esx-name"),
                             call("BIOS UUID: any-uuid"),
                             call("CPUs: 2"),
                             call("MemoryMB: 2048"),
                             call("Guest PowerState: any-guest-state"),
                             call("Guest Full Name: any-full-name"),
                             call("Guest Container Type: any-id"),
                             call("Container Version: any-version"),
                             call()
                         ])

    @patch("isphere.command.CachingVSphere.wait_for_tasks")
    @patch("isphere.command.CachingVSphere.retrieve")
    def test_should_reset_vms(self, cache_retrieve, _):
        self.vm_names.return_value = ["any-host-1", "any-host-2"]
        mock_vm1 = Mock()
        mock_vm2 = Mock()
        cache_retrieve.side_effect = [mock_vm1, mock_vm2]

        self.repl.do_reset("any.*")

        mock_vm1.ResetVM_Task.assert_called_with()
        mock_vm2.ResetVM_Task.assert_called_with()

    @patch("isphere.command.CachingVSphere.retrieve")
    def test_should_reboot_vms(self, cache_retrieve):
        self.vm_names.return_value = ["any-host-1", "any-host-2"]
        mock_vm1 = Mock()
        mock_vm2 = Mock()
        cache_retrieve.side_effect = [mock_vm1, mock_vm2]

        self.repl.do_reboot("any.*")

        mock_vm1.RebootGuest.assert_called_with()
        mock_vm2.RebootGuest.assert_called_with()

    @patch("isphere.command.CachingVSphere.retrieve")
    def test_should_print_config_for_matching_vms(self, cache_retrieve):
        self.vm_names.return_value = ["any-host-1"]
        mock_vm = Mock(config="Any vm config\nCould be several lines long.")
        cache_retrieve.return_value = mock_vm

        self.repl.do_config("any-host-1")

        self.assertEqual(self.mock_print.call_args_list,
                         [
                             call("----------------------------------------------------------------------"),
                             call("Config for any-host-1:"),
                             call("Any vm config\nCould be several lines long."),
                             call()
                         ])
