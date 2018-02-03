import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import * as actionCreators from '../../actions/auth';
import PropTypes from 'prop-types';

import { validate_token } from '../../utils/http_functions'

export interface AuthenticatedComponentProps{
    history: any,
    isAuthenticated: boolean,
    loginUserSuccess: (any) => any,
    getUserInformation: (any) => any,
    logout: () => any
}

export interface AuthenticatedComponentState{
    loaded_if_needed : boolean
}

function mapStateToProps(state) {
    return {
        token: state.auth.token,
        userName: state.auth.userName,
        isAuthenticated: state.auth.isAuthenticated,
    };
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators(actionCreators, dispatch);
}

export function requireAuthentication(Component) {
    class AuthenticatedComponent extends React.Component<AuthenticatedComponentProps,AuthenticatedComponentState> {

        constructor(props: any) {
            super(props);
            this.state = {loaded_if_needed: false};
            this.checkAuth = this.checkAuth.bind(this)
        }

        componentWillMount() {
            this.setState({
                loaded_if_needed: false,
            });
            this.checkAuth(this.props);
        }

        componentWillReceiveProps(nextProps) {
            this.checkAuth(nextProps);
        }

        checkAuth(props = this.props) {
            if (!props.isAuthenticated) {
                const token = localStorage.getItem('token');
                if (!token) {
                    props.history.push('/login');
                } else {
                    validate_token( token )
                        .then(res => {

                            if (res.status === 200) {
                                this.props.loginUserSuccess(token);
                                this.props.getUserInformation(token);
                                this.setState({loaded_if_needed: true});

                            } else {
                                localStorage.removeItem('token');
                                props.history.push('/login');
                            }
                        })
                        .catch(() => {
                            localStorage.removeItem('token');
                            props.history.push('/login');
                        });

                }
            } else {
                this.setState({loaded_if_needed: true});
                this.forceUpdate();
            }
        }


        render() {
            return (
                <div>
                    {(this.props.isAuthenticated && this.state.loaded_if_needed)
                        ? <Component {...this.props} />
                        : null
                    }
                </div>
            );

        }
    }

    return connect(mapStateToProps, mapDispatchToProps)(AuthenticatedComponent);
}
