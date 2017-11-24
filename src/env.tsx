


let env = { 'baseUrl': "" }

// NODE_ENV is either "development" or "production"
if (process.env.NODE_ENV === "development" ||
    process.env.NODE_ENV === "test") {
    env.baseUrl = "http://localhost:4200"
} else {
    env.baseUrl = ""
}

if (process.env.REACT_APP_BACKEND_PATH) {
    env.baseUrl = process.env.REACT_APP_BACKEND_PATH
}

if (process.env.NODE_ENV === "development") {
    console.log(env)
}
export default env;