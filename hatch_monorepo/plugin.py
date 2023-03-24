from contextlib import contextmanager, suppress

from hatch.env.plugin.interface import EnvironmentInterface
from hatch.utils.shells import ShellManager


class MonorepoEnvironment(EnvironmentInterface):
    PLUGIN_NAME = 'monorepo'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shells = ShellManager(self)
        self._parent_python = None

    @staticmethod
    def get_option_types() -> dict:
        # TODO Anything to add?
        return {}

    def activate(self):
        # Nothing to be done
        pass

    def deactivate(self):
        # Nothing to be done
        pass

    def find(self):
        return self.system_python

    def create(self):
        # Nothing to be done
        pass

    def remove(self):
        # Nothing to be done
        pass

    def exists(self):
        return False

    def install_project(self):
        with self.safe_activation():
            self.platform.check_command(self.construct_pip_install_command([self.apply_features(str(self.root))]))

    def install_project_dev_mode(self):
        with self.safe_activation():
            self.platform.check_command(
                self.construct_pip_install_command(['--editable', self.apply_features(str(self.root))])
            )

            for pyproject_path in self.root.glob("*/**/pyproject.toml"):
                print(f"{pyproject_path}...")
                self.platform.check_command(
                    self.construct_pip_install_command(['--editable', self.apply_features(str(pyproject_path.parent))])
                )

    def dependencies_in_sync(self):
        if not self.dependencies:
            return True

        from hatchling.dep.core import dependencies_in_sync

        with self.safe_activation():
            return dependencies_in_sync(self.dependencies_complex)

    def sync_dependencies(self):
        with self.safe_activation():
            self.platform.check_command(self.construct_pip_install_command(self.dependencies))

    @contextmanager
    def build_environment(self, dependencies):
        from hatchling.dep.core import dependencies_in_sync
        from packaging.requirements import Requirement

        with self.get_env_vars():
            if not dependencies_in_sync([Requirement(d) for d in dependencies]):
                self.platform.check_command(self.construct_pip_install_command(dependencies))

            yield

    def build_environment_exists(self):
        return True

    @contextmanager
    def command_context(self):
        with self.safe_activation():
            yield

    def enter_shell(self, name, path, args):
        shell_executor = getattr(self.shells, f'enter_{name}', None)
        if shell_executor is None:
            # Manually activate in lieu of an activation script
            with self.safe_activation():
                self.platform.exit_with_command([path, *args])
        else:
            with self.get_env_vars():
                shell_executor(path, args, self.system_python)

    def check_compatibility(self):
        super().check_compatibility()

        python_choice = self.config.get('python')
        if not python_choice:
            return

        with suppress(Exception):
            if self.parent_python:
                return

        message = f'cannot locate Python: {python_choice}'
        raise OSError(message)

    @property
    def parent_python(self):
        if self._parent_python is None:
            python_choice = self.config.get('python')
            if not python_choice:
                python_executable = self.system_python
            else:
                from virtualenv.discovery.builtin import get_interpreter

                python_executable = get_interpreter(python_choice, ()).executable

            self._parent_python = python_executable

        return self._parent_python

    @contextmanager
    def safe_activation(self):
        # Set user-defined environment variables first so ours take precedence
        with self.get_env_vars(), self:
            yield
