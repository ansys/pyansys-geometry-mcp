# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Configuration for MCP tool test modules."""

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
