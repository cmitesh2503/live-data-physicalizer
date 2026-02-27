import inspect
from google import adk
print('signature:', inspect.signature(adk.Agent))
print('doc:', adk.Agent.__doc__)
