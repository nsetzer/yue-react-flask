import * as React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import * as actionCreators from '../../actions/auth';

import { validate_token } from '../../utils/http_functions'

export interface DetermineAuthenticatedComponentProps{
    isAuthenticated: boolean,
    userName: string,
    token: string,
    loginUserSuccess: (any) => any,
}

export interface DetermineAuthenticatedComponentState{
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

export function DetermineAuth(Component) {

    class DetermineAuthenticatedComponent extends
        React.Component<DetermineAuthenticatedComponentProps,
                        DetermineAuthenticatedComponentState> {

        constructor(props: any) {
            super(props);
            this.state = {
                loaded_if_needed: false,
            };
        }

        componentWillMount() {
            this.checkAuth();
            this.setState({
                loaded_if_needed: false,
            });
        }

        componentWillReceiveProps(nextProps) {
            this.checkAuth(nextProps);
        }

        checkAuth(props = this.props) {
            if (!props.isAuthenticated) {
                const token = localStorage.getItem('token');
                if (token) {
                    validate_token( token )
                        .then(res => {
                            if (res.status === 200) {
                                this.props.loginUserSuccess(token);
                                this.setState({
                                    loaded_if_needed: true,
                                });

                            }
                        });
                }

            } else {
                this.setState({
                    loaded_if_needed: true,
                });
            }
        }

        render() {
            return (
                <div>
                    {this.state.loaded_if_needed
                        ? <Component {...this.props} />
                        : null
                    }
                </div>
            );

        }
    }

    return connect(mapStateToProps, mapDispatchToProps)(DetermineAuthenticatedComponent);
}
