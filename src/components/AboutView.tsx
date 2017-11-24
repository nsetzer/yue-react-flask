import * as React from 'react';
import { Link } from 'react-router-dom'

const logo = require('../svg/logo.svg');
import './App.css';

export interface AboutViewProps {
  match: any
}

export interface AboutViewState {
}

class AboutView extends React.Component<AboutViewProps, AboutViewState> {

  render() {
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">Welcome to React</h1>
        </header>

        <br/>
        <p>
        <Link to="/">&nbsp;Home&nbsp;</Link>
        <Link to="/login">&nbsp;Login&nbsp;</Link>
        <Link to="/register">&nbsp;Register&nbsp;</Link>
        <Link to="/test">&nbsp;Test&nbsp;</Link>
        </p>

        <br/>
        <p>
        <Link to="/about/React">&nbsp;React&nbsp;</Link>
        <Link to="/about/TypeScript">&nbsp;TypeScript&nbsp;</Link>
        <Link to="/about/Penguins">&nbsp;Penguins&nbsp;</Link>
        </p>

        <h1>{this.props.match.params.topic}</h1>

        Lorem ipsum


      </div>
    );
  }
}

export default AboutView;
