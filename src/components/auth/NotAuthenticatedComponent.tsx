import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import * as actionCreators from '../../actions/auth';
import PropTypes from 'prop-types';

import { validate_token } from '../../utils/http_functions'

export interface NotAuthenticatedComponentProps{
    history: any,
    isAuthenticated: boolean,
    loginUserSuccess: (any) => any,
}

export interface NotAuthenticatedComponentState{
    loaded : boolean
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

export function requireNoAuthentication(Component) {

    class NotAuthenticatedComponent extends
        React.Component<NotAuthenticatedComponentProps,
                        NotAuthenticatedComponentState> {

        constructor(props) {
            super(props);
            this.state = {
                loaded: false,
            };
            this.checkAuth = this.checkAuth.bind(this);
        }

        componentWillMount() {
            this.setState({loaded: false});
            this.checkAuth();
        }

        componentWillReceiveProps(nextProps) {
            this.checkAuth(nextProps);
        }

        checkAuth(props = this.props) {
            if (props.isAuthenticated) {
                props.history.push('/main');

            } else {
                const token = localStorage.getItem('token');
                if (token) {
                    validate_token( token )
                        .then(res => {
                            if (res.status === 200) {
                                this.props.loginUserSuccess(token);
                                props.history.push('/main');

                            } else {
                                this.setState({loaded: true});
                            }
                        });
                } else {
                    this.setState({loaded: true});
                }
            }
        }

        render() {
            return (
                <div>
                    {(!this.props.isAuthenticated && this.state.loaded)
                        ? <Component {...this.props} />
                        : null
                    }
                </div>
            );

        }
    }

    return connect(mapStateToProps, mapDispatchToProps)(NotAuthenticatedComponent);

}
