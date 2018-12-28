SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Use a set to store ARNs that are constantly failing.
# Aardvark will only log these errors at the INFO level
# instead of the ERROR level
FAILING_ARNS = set()
# FAILING_ARNS = {'ASDF', 'DEFG'}
