try:
    import src.interface.api
except Exception as e:
    import traceback
    with open("error.log", "w") as f:
        traceback.print_exc(file=f)
