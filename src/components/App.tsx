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
          <h1 className="App-title">Welcome to React</h1>
        </header>
        <br/>
        <p>
        <Link to="/login">&nbsp;Login&nbsp;</Link>
        <Link to="/register">&nbsp;Register&nbsp;</Link>
        </p>
        <p className="App-intro">
          Your App is Now Running<br/>
          To get started, edit <code>src/components/App.tsx</code> and save to reload.
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
