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

export interface ChangePasswordProps {
    changePassword: (password,redirect) => any,
    statusText: PropTypes.string,
};

export interface ChangePasswordState {
  password: string,
  verify_password: string,
  password_error_text: any,
  verify_password_error_text: any,
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

class ChangePassword extends React.Component<ChangePasswordProps,ChangePasswordState> {

  constructor(props) {
        super(props);
        const redirectFail = '/main';
        const redirectSuccess = '/main';
        this.state = {
            password: '',
            verify_password: '',
            password_error_text: null,
            verify_password_error_text: null,
            redirectFail: redirectFail,
            redirectSuccess: redirectSuccess,
            disabled: true,
        };
  }

  isDisabled() {
    let password_is_valid = false;
    let verify_password_is_valid = false;

    if (this.state.password === '' || !this.state.password) {
        this.setState({
            password_error_text: null,
        });
    } else {
      password_is_valid = true;
    }

    if (this.state.verify_password === '' || !this.state.verify_password) {
      this.setState({
            verify_password_error_text: null,
      });
    } else {
      verify_password_is_valid = true;
    }

    if (password_is_valid && verify_password_is_valid) {
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
                this.changePassword(e);
            }
        }
    }

  changePassword(e) {
      let state = {
        verify_password_error_text: "",
        password_error_text: "",
      }
      e.preventDefault();
      if (this.state.password.length < 5) {
        state.password_error_text = "Passwords must be more than 5 characters"
        this.setState(state)
        return
      } else if (this.state.verify_password !== this.state.password) {
        state.verify_password_error_text = "Passwords do not match"
        this.setState(state)
        return
      }
      this.props.changePassword(this.state.password, this.state.redirectSuccess);
  }

  render() {
    return (
      <div className="col-xs-12 col-md-6 col-md-offset-3" onKeyPress={(e) => this._handleKeyPress(e)}>
        <Grid container justify="center">
        <Grid item  xs={12} sm={6}>
        <Paper style={style}>
          <h2>Change Password</h2>
          {
              this.props.statusText &&
                  <div className="alert alert-info">
                      {this.props.statusText}
                  </div>
          }
          <form>
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

            <div className="col-md-12">
                <TextField
                  required
                  label="Verify Password"
                  type="password"
                  error={this.state.verify_password_error_text}
                  onChange={(e) => this.changeValue(e, 'verify_password')}
                />
            </div>
            {this.state.verify_password_error_text?<div>{this.state.verify_password_error_text}<br/></div>:null}

            <Button
              disabled={this.state.disabled}
              style={{ marginTop: 50 }}
              onClick={(e) => this.changePassword(e)}
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
        statusText: state.auth.changePasswordStatusText,
    };
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
    mapDispatchToProps
)(ChangePassword)
