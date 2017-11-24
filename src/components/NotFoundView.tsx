import * as React from 'react';
import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import * as actionCreators from '../actions/auth';

class NotFoundView extends React.Component {

    constructor(props: any) {
      super(props)
    }

    render() {
        return (
            <div className="col-xs-12 col-md-8 col-md-offset-4">
                <h1>Not Found</h1>
            </div>
        );
    }
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
export default connect(
  mapStateToProps,
  mapDispatchToProps
)(NotFoundView);
