import * as React from 'react';
import { Link } from 'react-router-dom'

import { connect } from 'react-redux';

const logo = require('../svg/logo.svg');
import './App.css';

class App extends React.Component {

  constructor(props) {
    super(props);
    this.state = {value: 0};
  }

  public render() {

    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">Welcome</h1>
        </header>
        <br/>
        <p>
        <Link to="/login">&nbsp;Login&nbsp;</Link>
        </p>
        <p className="App-intro">
        </p>
      </div>
    );
  }
}

function mapStateToProps(state) {
  return {
    };
}

function mapDispatchToProps(dispatch) {
  return {
    };
}

export default connect(
  mapStateToProps,
    mapDispatchToProps
)(App);
