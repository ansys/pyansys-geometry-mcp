# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for MCP tool test modules."""

from types import SimpleNamespace

import ansys.geometry.core as pyansys_geometry
import pytest


@pytest.fixture(scope="session")
def use_existing_service(request):
    value: str = request.config.getoption("--use-existing-service")
    return True if value.lower() == "yes" else False


@pytest.fixture(scope="session", autouse=True)
def use_tracker(request):
    """Fixture to enable or disable the tracker."""
    value: str = request.config.getoption("--use-tracker", default="no")  # Explicitly set default

    if value.lower() == "yes":
        pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = True
    else:
        pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = False

    yield  # This allows the test to run

    # Revert the state after the test session
    pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = False


@pytest.fixture(scope="session")
def transport_mode(request):
    """Fixture to determine transport mode to be used."""

    value: str = request.config.getoption("--transport-mode", default="insecure")

    return value.lower()


@pytest.fixture
def design():
    """Stub design with two bodies and one named selection."""
    box = SimpleNamespace(name="box")
    cyl = SimpleNamespace(name="cylinder")
    return SimpleNamespace(
        get_all_bodies=lambda: [box, cyl],
        named_selections=[
            SimpleNamespace(name="hot_side", bodies=[box]),
            SimpleNamespace(name="empty_group", bodies=[]),
        ],
    )


def pytest_addoption(parser):
    parser.addoption(
        "--use-existing-service",
        action="store",
        default="no",
        help=(
            "Use Modeler object to connect to an existing service. Options: 'yes' or 'no'."
            " By default, 'no'."
        ),
        choices=("yes", "no"),
    )
    parser.addoption(
        "--use-tracker",
        action="store",
        default="no",
        help=("Enable the tracker to update the design. Options: 'yes' or 'no'. By default, 'no'."),
        choices=("yes", "no"),
    )
    parser.addoption(
        "--transport-mode",
        action="store",
        default="insecure",
        help=("Specify the transport mode to use for the tests. By default, 'insecure'."),
        choices=("insecure", "uds", "wnua", "mtls"),
    )
    parser.addoption(
        "--run-llm-eval",
        action="store_true",
        default=False,
        help=(
            "Run the LLM tool-discoverability evaluation in tests/eval. Requires Azure OpenAI"
            " credentials in the environment. Skipped by default."
        ),
    )
    parser.addoption(
        "--llm-eval-repeats",
        action="store",
        type=int,
        default=5,
        help="Number of times each evaluation prompt is sent to the model. By default, 5.",
    )
    parser.addoption(
        "--llm-eval-threshold",
        action="store",
        type=float,
        default=0.8,
        help="Minimum fraction of repeats that must select the expected tool. By default, 0.8.",
    )
    parser.addoption(
        "--llm-eval-report",
        action="store",
        default="tests/logs/llm_eval_report.json",
        help="Path of the JSON report written by the evaluation suite.",
    )
