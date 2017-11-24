import * as React from 'react';
import PropTypes from 'prop-types';
//import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import * as actionCreators from '../actions/auth';

import TextField from 'material-ui/TextField';
import Button from 'material-ui/Button';
import Paper from 'material-ui/Paper';
import Grid from 'material-ui/Grid';

export interface LoginViewProps {
    loginUser: (a,b,c,d) => any,
    statusText: string,
};

export interface LoginViewState {
  email: string,
  password: string,
  email_error_text: any,
  password_error_text: any,
  redirectFail: string,
  redirectSuccess: string,
  disabled: boolean,
};

const style = {
    marginTop: 50,
    paddingBottom: 50,
    paddingTop: 25,
    width: '100%',
    textAlign: 'center',
    display: 'inline-block',
};

class LoginView extends React.Component<LoginViewProps,LoginViewState> {

  constructor(props) {
        super(props);
        const redirectFail = '/login';
        const redirectSuccess = '/main';
        this.state = {
            email: '',
            password: '',
            email_error_text: null,
            password_error_text: null,
            redirectFail: redirectFail,
            redirectSuccess: redirectSuccess,
            disabled: true,
        };
  }

  isDisabled() {
    let email_is_valid = false;
    let password_is_valid = false;

    if (this.state.email === '') {
        this.setState({
            email_error_text: null,
        });
    } else {
        email_is_valid = true;
    }
    /* else if (validateEmail(this.state.email)) {
        email_is_valid = true;
        this.setState({
            email_error_text: null,
        });

    } else {
        this.setState({
            email_error_text: 'Sorry, this is not a valid email',
        });
    }*/

    if (this.state.password === '' || !this.state.password) {
        this.setState({
            password_error_text: null,
        });
    } else {
        password_is_valid = true;
    }

    if (email_is_valid && password_is_valid) {
        this.setState({
            disabled: false,
        });
    }
  }

  changeValue(e, type) {
        const value = e.target.value;
        const next_state = {};
        next_state[type] = value;
        this.setState(next_state, () => {
            this.isDisabled();
        });
    }

  _handleKeyPress(e) {
        if (e.key === 'Enter') {
            if (!this.state.disabled) {
                this.login(e);
            }
        }
    }

  login(e) {
      let state = {
        password_error_text: "",
        email_error_text: "",
      }
      e.preventDefault();
      if (this.state.password.length < 5) {
        state.password_error_text = "Passwords must be more than 5 characters"
        this.setState(state)
        return
      }
      this.props.loginUser(this.props, this.state.email, this.state.password, this.state.redirectSuccess);
  }

  render() {
    return (

      <div onKeyPress={(e) => this._handleKeyPress(e)}>
        <Grid container justify="center">
        <Grid item  xs={12} sm={6}>
        <Paper style={style}>
          {
              this.props.statusText &&
                  <div className="alert alert-info">
                      {this.props.statusText}
                  </div>
          }
          <h2>Login</h2>
          <form>
            <div className="col-md-12">
                <TextField
                  required
                  label="Email"
                  type="email"
                  error={this.state.email_error_text}
                  onChange={(e) => this.changeValue(e, 'email')}
                />
            </div>
            {
                this.state.email_error_text ?
                    <div>{this.state.email_error_text}<br/></div> :
                    null
            }
            <div className="col-md-12">
                <TextField
                  required
                  label="Password"
                  type="password"
                  error={this.state.password_error_text}
                  onChange={(e) => this.changeValue(e, 'password')}
                />
            </div>
            {this.state.password_error_text?<div>{this.state.password_error_text}<br/></div>:null}

            <Button
              raised={true}
              disabled={this.state.disabled}
              style={{ marginTop: 50 }}
              onClick={(e) => this.login(e)}
            >Submit</Button>
          </form>
        </Paper>
        </Grid>
        </Grid>
      </div>
    );
  }
};

function mapStateToProps(state) {
    return {
        isAuthenticating: state.auth.isAuthenticating,
        statusText: state.auth.statusText,
    };
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
    mapDispatchToProps
)(LoginView);