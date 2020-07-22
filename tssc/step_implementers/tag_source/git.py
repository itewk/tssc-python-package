"""
Step Implementer for the tag-source step for Git.
"""
import sh
from tssc import TSSCFactory
from tssc import StepImplementer
from tssc import DefaultSteps

DEFAULT_ARGS = {}

OPTIONAL_ARGS = {
    'username': None,
    'password': None
}

class Git(StepImplementer):
    """
    StepImplementer for the tag-source step for Git.

    This makes extensive use of the python sh library. This was a deliberate choice,
    as the gitpython library doesn't appear to easily support username/password auth
    for http and https git repos, and that is a desired use case.

    Raises
    ------
    ValueError
        If a required parameter is unspecified
    RuntimeError
        If git commands fail for any reason
    """

    def __init__(self, config, results_dir, results_file_name):
        super().__init__(config, results_dir, results_file_name, DEFAULT_ARGS)

    @classmethod
    def step_name(cls):
        return DefaultSteps.TAG_SOURCE

    def _validate_step_config(self, step_config):
        """
        Function for implementers to override to do custom step config validation.

        Parameters
        ----------
        step_config : dict
            Step configuration to validate.
        """
        print(step_config)

    @staticmethod
    def _validate_runtime_step_config(runtime_step_config):
        if not all(element in runtime_step_config for element in OPTIONAL_ARGS) \
          and any(element in runtime_step_config for element in OPTIONAL_ARGS):
            raise ValueError('Either username or password is not set. Neither ' \
              'or both must be set.')

    def _get_tag(self):
        tag = 'latest'
        if(self.get_step_results('generate-metadata') \
          and self.get_step_results('generate-metadata').get('image-tag')):
            tag = self.get_step_results('generate-metadata').get('image-tag')
        else:
            print('No version found in metadata. Using latest')
        return tag

    def _run_step(self, runtime_step_config):
        username = None
        password = None


        self._validate_runtime_step_config(runtime_step_config)

        if any(element in runtime_step_config for element in OPTIONAL_ARGS):
            if(runtime_step_config.get('username') \
              and runtime_step_config.get('password')):
                username = runtime_step_config.get('username')
                password = runtime_step_config.get('password')
            else:
                raise ValueError('Both username and password must have ' \
                  'non-empty value in the runtime step configuration')
        else:
            print('No username/password found, assuming ssh')
        tag = self._get_tag()
        self._git_tag(tag)
        git_url = self._git_url(runtime_step_config)
        if git_url.startswith('http://'):
            if username and password:
                self._git_push('http://' + username + ':' + password + '@' + git_url[7:])
            else:
                raise ValueError('For a http:// git url, you need to also provide ' \
                  'username/password pair')
        elif git_url.startswith('https://'):
            if username and password:
                self._git_push('https://' + username + ':' + password + '@' + git_url[8:])
            else:
                raise ValueError('For a https:// git url, you need to also provide ' \
                  'username/password pair')
        else:
            self._git_push(None)
        results = {
            'git_tag' : tag
        }
        return results

    @staticmethod
    def _git_url(runtime_step_config):
        return_val = None
        if runtime_step_config.get('git_url'):
            return_val = runtime_step_config.get('git_url')
        else:
            git_config = sh.git.bake("config")
            try:
                return_val = git_config(
                    '--get',
                    'remote.origin.url').stdout.decode("utf-8").rstrip()
            except sh.ErrorReturnCode:  # pylint: disable=undefined-variable # pragma: no cover
                raise RuntimeError('Error invoking git config --get remote.origin.url')
        return return_val

    @staticmethod
    def _git_tag(git_tag_value): # pragma: no cover
        git_tag = sh.git.bake("tag")
        try:
            git_tag(git_tag_value)
        except sh.ErrorReturnCode:  # pylint: disable=undefined-variable
            raise RuntimeError('Error invoking git tag ' + git_tag_value)

    @staticmethod
    def _git_push(url=None): # pragma: no cover
        git_push = sh.git.bake("push")
        try:
            if url:
                git_push(
                    url,
                    '--tag')
            else:
                git_push('--tag')
        except sh.ErrorReturnCode:  # pylint: disable=undefined-variable
            raise RuntimeError('Error invoking git push')

# register step implementer
TSSCFactory.register_step_implementer(Git, True)