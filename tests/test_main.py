import sys
from unittest.mock import patch, ANY
from ward import test
from remake.main import main
from remake.context import isVerbose, unsetVerbose, isRebuild, unsetRebuild, isClean, unsetClean, isDryRun, unsetDryRun
import io


# Helper to reset all global flags
def _reset_all_flags():
    unsetVerbose()
    unsetDryRun()
    unsetClean()
    unsetRebuild()


@test("main function handles --verbose flag")
def test_main_verbose():
    """Verify that 'main' correctly handles the --verbose flag."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--verbose']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isVerbose() is True
            assert not isDryRun()
            assert not isClean()
            assert not isRebuild()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --dry-run flag (implies --verbose)")
def test_main_dry_run():
    """Verify that 'main' correctly handles the --dry-run flag and implies --verbose."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--dry-run']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isDryRun() is True
            assert isVerbose() is True  # dry-run implies verbose
            assert not isClean()
            assert not isRebuild()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --clean flag")
def test_main_clean():
    """Verify that 'main' correctly handles the --clean flag."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--clean']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isClean() is True
            assert not isVerbose()
            assert not isDryRun()
            assert not isRebuild()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --rebuild flag")
def test_main_rebuild():
    """Verify that 'main' correctly handles the --rebuild flag."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--rebuild']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isRebuild() is True
            assert not isVerbose()
            assert not isDryRun()
            assert not isClean()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --config-file flag")
def test_main_config_file():
    """Verify that 'main' correctly handles the --config-file flag."""
    _reset_all_flags()
    test_config_file = "ReMakeFile.test"
    with patch.object(sys, 'argv', ['remake', '-f', test_config_file]):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            mock_execute.assert_called_once_with(ANY, configFile=test_config_file, targets=None)
    _reset_all_flags()


@test("main function handles multiple targets")
def test_main_multiple_targets():
    """Verify that 'main' correctly identifies and passes multiple targets."""
    _reset_all_flags()
    targets = ['/tmp/target1', 'target2']
    with patch.object(sys, 'argv', ['remake'] + targets):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=targets)
    _reset_all_flags()


@test("main function handles --verbose and --clean flags")
def test_main_verbose_clean():
    """Verify that 'main' correctly handles --verbose and --clean flags."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--verbose', '--clean']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isVerbose() is True
            assert isClean() is True
            assert not isDryRun()
            assert not isRebuild()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --dry-run and --clean flags")
def test_main_dry_run_clean():
    """Verify that 'main' correctly handles --dry-run and --clean flags."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--dry-run', '--clean']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isDryRun() is True
            assert isClean() is True
            assert isVerbose() is True  # dry-run implies verbose
            assert not isRebuild()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function errors when --clean and --rebuild are used together")
def test_main_clean_rebuild_errors():
    """Verify that 'main' errors if both --clean and --rebuild are provided."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--clean', '--rebuild']):
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            try:
                main()
                # If main() does not raise SystemExit, fail the test
                assert False, "main() did not exit as expected"
            except SystemExit as e:
                assert e.code == 2
            # The error message from argparse for mutually exclusive arguments is something like:
            # "argument -r/--rebuild: not allowed with argument -c/--clean"
            assert "not allowed with" in mock_stderr.getvalue()
    _reset_all_flags()


@test("main function handles --verbose and --rebuild flags")
def test_main_verbose_rebuild():
    """Verify that 'main' correctly handles --verbose and --rebuild flags."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--verbose', '--rebuild']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isVerbose() is True
            assert isRebuild() is True
            assert not isDryRun()
            assert not isClean()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --dry-run and --rebuild flags")
def test_main_dry_run_rebuild():
    """Verify that 'main' correctly handles --dry-run and --rebuild flags."""
    _reset_all_flags()
    with patch.object(sys, 'argv', ['remake', '--dry-run', '--rebuild']):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isDryRun() is True
            assert isRebuild() is True
            assert isVerbose() is True  # dry-run implies verbose
            assert not isClean()
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=None)
    _reset_all_flags()


@test("main function handles --config-file and target")
def test_main_config_file_and_target():
    """Verify that 'main' correctly handles --config-file and a target."""
    _reset_all_flags()
    test_config_file = "AnotherReMakeFile"
    targets = ['final_target']
    with patch.object(sys, 'argv', ['remake', '-f', test_config_file] + targets):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            mock_execute.assert_called_once_with(ANY, configFile=test_config_file, targets=targets)
    _reset_all_flags()


@test("main function handles --clean with specific targets")
def test_main_clean_specific_targets():
    """Verify that 'main' correctly handles --clean with specific targets."""
    _reset_all_flags()
    targets = ['/tmp/target1', 'target2']
    with patch.object(sys, 'argv', ['remake', '--clean'] + targets):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isClean() is True
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=targets)
    _reset_all_flags()


@test("main function handles --rebuild with specific targets")
def test_main_rebuild_specific_targets():
    """Verify that 'main' correctly handles --rebuild with specific targets."""
    _reset_all_flags()
    targets = ['/tmp/target1', 'target2']
    with patch.object(sys, 'argv', ['remake', '--rebuild'] + targets):
        with patch('remake.main.executeReMakeFileFromDirectory') as mock_execute:
            main()
            assert isRebuild() is True
            mock_execute.assert_called_once_with(ANY, configFile=ANY, targets=targets)
    _reset_all_flags()