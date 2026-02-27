from google import adk
import inspect

print([attr for attr in dir(adk) if 'Invocation' in attr])
print('tools:', [attr for attr in dir(adk.tools) if 'Invocation' in attr])

# maybe check module path
try:
    IC = adk.InvocationContext
    print('IC found', IC)
    print('signature', inspect.signature(IC))
except Exception as e:
    print('InvocationContext not in adk directly', e)
