"""
Skills Service
"""

import subprocess
import re


class SkillsService:

    def check(self):

        try:

            result = subprocess.run(

                [
                    "openclaw",
                    "skills",
                    "check"
                ],

                capture_output=True,
                text=True

            )

            return result.stdout

        except Exception as e:

            return str(e)

    def status(self):

        output = self.check()

        skills = []

        mode = None

        for line in output.splitlines():

            line = line.strip()

            if line == "Ready and visible to model:":

                mode = "ready"
                continue

            if line == "Missing requirements:":

                mode = "missing"
                continue

            if not line:

                continue

            if mode == "ready":

                skills.append({

                    "name": line,

                    "status": "ready"

                })

            elif mode == "missing":

                if line.startswith("Tip:"):

                    break

                name = re.sub(

                    r"\s*\(.*",

                    "",

                    line

                )

                skills.append({

                    "name": name,

                    "status": "missing"

                })

        return skills

    def list(self):

        try:

            result = subprocess.run(

                [
                    "openclaw",
                    "skills",
                    "list"
                ],

                capture_output=True,
                text=True

            )

            return result.stdout

        except Exception as e:

            return str(e)

    def info(self, skill):

        try:

            result = subprocess.run(

                [
                    "openclaw",
                    "skills",
                    "info",
                    skill
                ],

                capture_output=True,
                text=True

            )

            return result.stdout

        except Exception as e:

            return str(e)