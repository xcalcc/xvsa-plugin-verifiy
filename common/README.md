# Pycommon - Python Common Utilities and Definitions
 This is a module to put those definitions and common utilities 
 where we may leverage to enhance our cross-component implementation unification.
 
 This is also an optimal place for failure test (failure injection)
 
# Principles in the module
- Utilities used across components
- System specific implementation or OS dependent logic (such as file reading / writing)
- Environment checking and System status detection
- Error Handling and Error code definition


# Usage
- Put the parent directory of the directory common in the PYTHONPATH of your project
- See the docs in docs folder