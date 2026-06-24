import importlib
import sys
import types
from unittest.mock import Mock, patch


class TestCommitterRegression:
    @staticmethod
    def _import_committer_module():
        mock_sysmlv2_client = types.ModuleType("sysmlv2_client")
        mock_sysmlv2_client.SysMLV2Client = Mock()

        mock_api_lib = types.ModuleType("sysml_api.api_lib")
        mock_api_lib.create_sysml_project = Mock()
        mock_api_lib.get_project_by_name = Mock()
        mock_api_lib.commit_to_project = Mock()

        mock_sysml_api = types.ModuleType("sysml_api")
        mock_sysml_api.api_lib = mock_api_lib

        with patch.dict(
            "sys.modules",
            {
                "sysmlv2_client": mock_sysmlv2_client,
                "sysml_api": mock_sysml_api,
                "sysml_api.api_lib": mock_api_lib,
            },
        ):
            sys.modules.pop("flexo_syside_lib.committer", None)
            return importlib.import_module("flexo_syside_lib.committer")

    def test_commit_sysml_to_flexo_forwards_default_commit_flags(self):
        committer = self._import_committer_module()

        with patch.object(committer, "SysMLV2Client", return_value=Mock()), patch.object(
            committer, "convert_sysml_string_textual_to_json", return_value=('{"change": 1}', "[]")
        ), patch.object(committer, "get_project_by_name", return_value=({"name": "Demo"}, "project-123")), patch.object(
            committer, "commit_to_project", return_value=({"status": "ok"}, "commit-123")
        ) as mock_commit:
            result = committer.commit_sysml_to_flexo(
                sysml_output="package Demo {}",
                project_name="Demo",
                api_key="token",
                verbose=False,
            )

        assert result["project_id"] == "project-123"
        assert result["commit_id"] == "commit-123"
        assert mock_commit.call_args.args[1:] == ("project-123", '{"change": 1}')
        assert mock_commit.call_args.kwargs == {
            "delete_project_data": False,
            "replace_model": False,
        }

    def test_commit_sysml_to_flexo_forwards_explicit_commit_flags(self):
        committer = self._import_committer_module()

        with patch.object(committer, "SysMLV2Client", return_value=Mock()), patch.object(
            committer, "convert_sysml_string_textual_to_json", return_value=('{"change": 1}', "[]")
        ), patch.object(committer, "get_project_by_name", return_value=({"name": "Demo"}, "project-123")), patch.object(
            committer, "commit_to_project", return_value=({"status": "ok"}, "commit-123")
        ) as mock_commit:
            result = committer.commit_sysml_to_flexo(
                sysml_output="package Demo {}",
                project_name="Demo",
                api_key="token",
                verbose=False,
                delete_project_data=True,
                replace_model=True,
            )

        assert result["project_id"] == "project-123"
        assert result["commit_id"] == "commit-123"
        assert mock_commit.call_args.args[1:] == ("project-123", '{"change": 1}')
        assert mock_commit.call_args.kwargs == {
            "delete_project_data": True,
            "replace_model": True,
        }
