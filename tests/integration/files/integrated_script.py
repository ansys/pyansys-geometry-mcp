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

doc = GetActiveDocument()
radius = MM(int(argsDict["radius"]))

sphere = Sphere.Create(Frame.World, radius)
u_range = Interval.Create(0, 2 * math.pi)
v_range = Interval.Create(-math.pi / 2, math.pi / 2)
box = BoxUV.Create(u_range, v_range)
b = Body.CreateSurfaceBody(sphere, box)
db = DesignBody.Create(doc.MainPart, "sphere", b)

numBodies = doc.MainPart.Bodies.Count

result = {"numBodies": numBodies}
