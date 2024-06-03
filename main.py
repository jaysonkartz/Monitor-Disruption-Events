import argparse

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-n", "--name", required=False, help="name of the user",default="John Doe",type=str)

ap.add_argument("-d", "--days", required=True, help="Max No days published before",default=7,type=int)
# ap.add_argument("-n", "--name", required=True, help="name of the user")

args = vars(ap.parse_args())

# display a friendly message to the user
print("Hi there {}, it's nice to meet you!".format(args["name"]))
print(f'Running script to scrape data for {args["days"]} days.')